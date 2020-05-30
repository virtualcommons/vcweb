import itertools
import logging
import mimetypes
import uuid
from collections import defaultdict

import unicodecsv
from contact_form.views import ContactFormView
from dal import autocomplete
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as ContribAuthLoginView, LogoutView as ContribAuthLogoutView
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import models
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import FormView, TemplateView, ListView
from django.views.generic.detail import SingleObjectMixin
from rest_framework import viewsets, status, renderers
from rest_framework.decorators import action
from rest_framework.response import Response

from .api import SUCCESS_DICT, FAILURE_DICT, create_message_event
from .decorators import (anonymous_required, is_participant, is_experimenter, ownership_required, group_required)
from .forms import (ParticipantAccountForm, ExperimenterAccountForm, UpdateExperimentForm,
                    AsuRegistrationForm, RegisterEmailListParticipantsForm, RegisterTestParticipantsForm,
                    BookmarkExperimentMetadataForm, ExperimentConfigurationForm, ExperimentParameterValueForm,
                    RoundConfigurationForm, RoundParameterValueForm, AntiSpamContactForm, PortOfMarsSignupForm)
from .http import JsonResponse, dumps
from .models import (User, ChatMessage, Participant, ParticipantExperimentRelationship, ParticipantGroupRelationship,
                     ExperimentConfiguration, Experiment, Institution, BookmarkedExperimentMetadata, OstromlabFaqEntry,
                     ExperimentParameterValue, RoundConfiguration, RoundParameterValue, ParticipantSignup,
                     get_model_fields, PermissionGroup, get_audit_data, )
from .permissions import CanEditExperiment
from .serializers import ExperimentSerializer, ExperimentRegistrationSerializer
from ..redis_pubsub import RedisPubSub

logger = logging.getLogger(__name__)


class AnonymousMixin(object):

    """ provides the anonymous_required decorator """

    @method_decorator(anonymous_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ParticipateView(TemplateView):

    @method_decorator(group_required(PermissionGroup.participant, PermissionGroup.demo_participant))
    def dispatch(self, *args, **kwargs):
        participant = self.request.user.participant
        experiment = get_active_experiment(participant)
        if experiment is None:
            return redirect('core:dashboard')
        else:
            return redirect(experiment.participant_url)


class DashboardViewModel(object):

    @staticmethod
    def create(user, *args, **kwargs):
        if user is None or not user.is_active:
            logger.error("can't create dashboard view model from invalid user %s", user)
            raise ValueError("invalid user: %s" % user)
        klass = ExperimenterDashboardViewModel if is_experimenter(user) else ParticipantDashboardViewModel
        return klass(user, *args, **kwargs)

    def to_json(self):
        return dumps(self.to_dict())


class ExperimenterDashboardViewModel(DashboardViewModel):
    template_name = 'experimenter/dashboard.html'

    def __init__(self, user, *args, **kwargs):
        self.experimenter = user.experimenter
        _configuration_cache = {}
        self.experiment_metadata_dict = defaultdict(list)
        for ec in ExperimentConfiguration.objects.active():
            self.experiment_metadata_dict[ec.experiment_metadata].append(ec)
            _configuration_cache[ec.pk] = ec
        self.experiment_metadata_list = []
        bem_pks = BookmarkedExperimentMetadata.objects.filter(
            experimenter=self.experimenter).values_list('experiment_metadata', flat=True)
        for em, ecs in list(self.experiment_metadata_dict.items()):
            d = em.to_dict(include_configurations=True, configurations=ecs)
            d['bookmarked'] = em.pk in bem_pks
            self.experiment_metadata_list.append(d)

        experiment_status_dict = defaultdict(list)
        for e in Experiment.objects.for_experimenter(self.experimenter).order_by('-pk'):
            e.experiment_configuration = _configuration_cache[e.experiment_configuration.pk]
            experiment_status_dict[e.status].append(
                e.to_dict(attrs=('monitor_url', 'status_line',)))
        self.pending_experiments = experiment_status_dict['INACTIVE']
        self.running_experiments = experiment_status_dict['ACTIVE'] + experiment_status_dict['ROUND_IN_PROGRESS']
        self.archived_experiments = experiment_status_dict['COMPLETED']

    def to_dict(self):
        return {
            'experimentMetadataList': self.experiment_metadata_list,
            'pendingExperiments': self.pending_experiments,
            'runningExperiments': self.running_experiments,
            'archivedExperiments': self.archived_experiments,
            'experimenterId': self.experimenter.pk,
            'isAdmin': self.experimenter.is_superuser
        }


class ParticipantDashboardViewModel(DashboardViewModel):
    template_name = 'participant/dashboard.html'

    def __init__(self, user, *args, **kwargs):
        self.participant = user.participant
        experiment_status_dict = defaultdict(list)
        for e in self.participant.experiments.select_related('experiment_configuration').all():
            experiment_status_dict[e.status].append(
                e.to_dict(attrs=('participant_url', 'start_date'), name=e.experiment_metadata.title))
        self.pending_experiments = experiment_status_dict['INACTIVE']
        self.running_experiments = experiment_status_dict['ACTIVE'] + experiment_status_dict['ROUND_IN_PROGRESS']
        upcoming_signups = ParticipantSignup.objects.upcoming(self.participant)
        self.show_end_dates = False
        self.signups = []
        for signup in upcoming_signups:
            if not signup.invitation.experiment_session.is_same_day:
                self.show_end_dates = True
            self.signups.append(signup.to_dict())

    def to_dict(self):
        return {
            'pendingExperiments': self.pending_experiments,
            'runningExperiments': self.running_experiments,
            'signups': self.signups,
            'showEndDates': self.show_end_dates,
            'isPortOfMars': self.participant.is_port_of_mars_participant()
        }


def csrf_failure(request, reason=""):
    logger.error("csrf failure on %s due to %s", request, reason)
    return render(request, 'invalid_request.html', {"message": 'Sorry, we were unable to process your request.'})


@login_required
@require_GET
def dashboard(request):
    """
    selects the appropriate dashboard template and data for participants and experimenters
    """
    user = request.user
    logger.debug("handling dashboard request for user %s", user)
    if is_participant(user):
        participant = user.participant
        # special case for if this participant needs to update their profile or if they have pending invitations to
        # respond to immediately.
        if participant.should_update_profile:
            # redirect to the profile page if this is a non-demo participant
            # and their profile is incomplete
            return redirect('core:profile')
        elif participant.has_pending_invitations:
            return redirect('subjectpool:experiment_session_signup')
    dashboard_view_model = DashboardViewModel.create(user)
    return render(request, dashboard_view_model.template_name,
                  {'dashboardViewModelJson': dashboard_view_model.to_json()})


@login_required
@group_required(PermissionGroup.participant)
@require_GET
def cas_asu_registration(request):
    user = request.user
    if is_participant(user) and user.participant.should_update_profile:
        return render(request, 'accounts/asu_registration.html',
                      {'form': AsuRegistrationForm(instance=user.participant)})
    else:
        return redirect('core:dashboard')


@group_required(PermissionGroup.participant)
@require_POST
def cas_asu_registration_submit(request):
    participant = request.user.participant
    form = AsuRegistrationForm(request.POST or None, instance=participant)
    if form.is_valid():
        form.save()
        messages.info(request, _("You've been successfully registered with our mailing list. Thanks!"))
        logger.debug("created new participant from asurite registration: %s", participant)
        return redirect('core:dashboard')
    else:
        return redirect('core:cas_asu_registration')


@login_required
@require_GET
def get_dashboard_view_model(request):
    return JsonResponse({
        'success': True,
        'dashboardViewModelJson': DashboardViewModel.create(request.user).to_json()
    })


def set_authentication_token(user, authentication_token=''):
    commons_user = None
    # FIXME: ugliness. see if we can refactor this
    if is_participant(user):
        commons_user = user.participant
    elif is_experimenter(user):
        commons_user = user.experimenter
    else:
        logger.error("Invalid user: %s", user)
        raise ValueError("User was not a participant or experimenter")
    logger.debug("setting %s authentication_token=%s", commons_user, authentication_token)
    commons_user.update_authentication_token(authentication_token)
    RedisPubSub.get_redis_instance().set("%s_%s" % (user.email, user.pk), authentication_token)


def get_active_experiment(participant, experiment_metadata=None, **kwargs):
    pers = []
    criteria = dict(participant=participant, **kwargs)
    if experiment_metadata is not None:
        criteria.update(experiment__experiment_metadata=experiment_metadata)
    pers = ParticipantExperimentRelationship.objects.active(**criteria)
    if pers.exists():
        logger.debug("using first active experiment %s for participant %s", pers[0], participant)
        return pers[0].experiment
    return None


class PortOfMarsSignupView(FormView):
    form_class = PortOfMarsSignupForm
    template_name = 'accounts/port_of_mars_registration_form.html'
    success_url = '/dashboard/'

    def form_valid(self, form):
        response = super().form_valid(form)
        self.register(form)
        return response

    @transaction.atomic
    def register(self, form):
        institution = Institution.objects.get(name='Arizona State University')
        user = form.save()
        participant = Participant.objects.create(user=user, institution=institution, can_receive_invitations=True)
        participant.add_to_port_of_mars_group()
        user.save()
        auth.login(self.request, user, backend='vcweb.core.backends.EmailAuthenticationBackend')
        return user


class LoginView(AnonymousMixin, ContribAuthLoginView):
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()
        set_authentication_token(user, self.request.session.session_key)
        return response


class LogoutView(LoginRequiredMixin, ContribAuthLogoutView):

    def dispatch(self, request, *args, **kwargs):
        # clear auth tokens
        user = request.user
        if not user.is_anonymous:
            set_authentication_token(user)
        return super().dispatch(request, *args, **kwargs)


@login_required
@require_GET
def account_profile(request):
    user = request.user
    if is_participant(user):
        form = ParticipantAccountForm(instance=user.participant)
    else:
        form = ExperimenterAccountForm(instance=user.experimenter)
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
@group_required(PermissionGroup.experimenter, PermissionGroup.participant)
@require_POST
def update_account_profile(request):
    user = request.user
    if is_experimenter(user):
        form = ExperimenterAccountForm(request.POST or None, instance=user.experimenter)
    else:
        form = ParticipantAccountForm(request.POST or None, instance=user.participant)

    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})
    return JsonResponse({'success': False, 'message': 'Something went wrong. Please try again.'})


class SingleExperimentMixin(SingleObjectMixin):
    model = Experiment
    context_object_name = 'experiment'

    # FIXME: is this the right place for this?  Useful when a form mixes this
    # class in.
    def get_initial(self):
        self.object = self.get_object()
        return {"experiment_pk": self.object.pk}

    def process(self):
        pass

    def can_access_experiment(self, user, experiment):
        return True

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk')
        experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration', 'experimenter'), pk=pk)
        user = self.request.user
        if self.can_access_experiment(user, experiment):
            return experiment
        else:
            logger.warning("unauthorized access by user %s to experiment %s", user, experiment)
            raise PermissionDenied("You do not have access to %s" % experiment)


class ExperimenterSingleExperimentMixin(SingleExperimentMixin):

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.process()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def can_access_experiment(self, user, experiment):
        return is_experimenter(user, experiment.experimenter)


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@require_POST
def toggle_bookmark_experiment_metadata(request):
    form = BookmarkExperimentMetadataForm(request.POST or None)
    if form.is_valid():
        experimenter = form.cleaned_data.get('experimenter')
        experiment_metadata = form.cleaned_data.get('experiment_metadata')
        if request.user.experimenter == experimenter:
            bem, created = BookmarkedExperimentMetadata.objects.get_or_create(experiment_metadata=experiment_metadata,
                                                                              experimenter=experimenter)
            if not created:
                # toggle deletion, remove this bookmark
                logger.debug("Deleting existing bookmark: %s", bem)
                bem.delete()
            return JsonResponse(SUCCESS_DICT)
        else:
            logger.warn("Invalid toggle bookmark experiment metadata request: %s", request)
    return JsonResponse(FAILURE_DICT)


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@ownership_required(Experiment)
@require_GET
def monitor(request, pk=None):
    experiment = get_object_or_404(Experiment.objects.select_related(
        'experiment_configuration', 'experimenter'), pk=pk)

    return render(request, 'experimenter/monitor.html', {
        'experiment': experiment,
        'experimentModelJson': experiment.to_json(include_round_data=True),
    })


@method_decorator(group_required(PermissionGroup.experimenter), name='dispatch')
class BaseExperimentRegistrationView(ExperimenterSingleExperimentMixin, FormView):

    def get_initial(self):
        # sets initial values for several form fields in the register participants form
        # based on the experiment
        _initial = super(BaseExperimentRegistrationView, self).get_initial()
        experiment = self.object
        logger.debug("SETTING OBJECT %s", self.object)
        _initial.update(
            registration_email_from_address=experiment.experimenter.email,
            experiment_password=experiment.authentication_code,
            registration_email_subject=experiment.registration_email_subject,
            registration_email_text=experiment.registration_email_text,
            sender=experiment.experimenter.full_name,
        )
        return _initial

    def form_valid(self, form):
        experiment = self.get_object()
        experiment.authentication_code = form.cleaned_data.get('experiment_password')
        for field in ('start_date', 'registration_email_subject', 'registration_email_text'):
            setattr(experiment, field, form.cleaned_data.get(field))
        experiment.save()
        return super(BaseExperimentRegistrationView, self).form_valid(form)

    def get_success_url(self):
        return reverse('core:monitor_experiment', kwargs={'pk': self.get_object().pk})


class RegisterEmailListView(BaseExperimentRegistrationView):
    form_class = RegisterEmailListParticipantsForm
    template_name = 'experimenter/register-email-participants.html'

    def form_valid(self, form):
        valid = super(RegisterEmailListView, self).form_valid(form)
        emails = form.cleaned_data.get('participant_emails')
        send_email = form.cleaned_data.get('send_email')
        institution = form.cleaned_data.get('institution')
        sender = form.cleaned_data.get('sender')
        from_email = form.cleaned_data.get('registration_email_from_address')
        experiment = self.get_object()
        logger.debug("registering participants %s at institution %s for experiment %s", emails, institution,
                     experiment)
        experiment.register_participants(emails=emails, institution=institution,
                                         password=experiment.authentication_code,
                                         sender=sender, from_email=from_email,
                                         send_email=send_email)
        return valid


class ManageExperimentViewSet(viewsets.ModelViewSet):
    serializer_class = ExperimentSerializer
    permission_classes = [CanEditExperiment]
    renderer_classes = (renderers.TemplateHTMLRenderer, renderers.JSONRenderer)

    @action(detail=True, methods=['post'])
    def submit_register_test_participants(self, request, pk=None):
        experiment = self.get_object()
        serializer = ExperimentRegistrationSerializer(data=request.data, experiment=experiment)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True})
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return Experiment.objects.viewable(self.request.user)


class RegisterTestParticipantsView(BaseExperimentRegistrationView):
    form_class = RegisterTestParticipantsForm
    template_name = 'experimenter/register-test-participants.html'

    def form_valid(self, form):
        valid = super(RegisterTestParticipantsView, self).form_valid(form)
        if valid:
            number_of_participants = form.cleaned_data.get('number_of_participants')
            username_suffix = form.cleaned_data.get('username_suffix')
            email_suffix = form.cleaned_data.get('email_suffix')
            institution = form.cleaned_data.get('institution')
            experiment = self.get_object()
            experiment.setup_demo_participants(count=number_of_participants,
                                               institution=institution,
                                               email_suffix=email_suffix,
                                               username_suffix=username_suffix)
        return valid


class DataExportMixin(ExperimenterSingleExperimentMixin):
    file_extension = '.csv'

    def render_to_response(self, context, **response_kwargs):
        experiment = self.get_object()
        file_ext = self.file_extension
        if file_ext in mimetypes.types_map:
            content_type = mimetypes.types_map[file_ext]
        else:
            content_type = 'application/octet-stream'
        response = HttpResponse(content_type=content_type)
        response[
            'Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name(file_ext=file_ext)
        self.export_data(response, experiment)
        return response


class CsvDataExporter(DataExportMixin):

    def export_data(self, response, experiment):
        writer = unicodecsv.writer(response, encoding='utf-8')
        writer.writerow(['Group', 'Members'])
        for group in experiment.group_set.all():
            writer.writerow(
                itertools.chain.from_iterable([[group], group.participant_set.all()]))
        for round_data in experiment.round_data_set.all():
            round_configuration = round_data.round_configuration
            # write out group-wide and participant data values
            writer.writerow(['Owner', 'Round', 'Data Parameter',
                             'Data Parameter Value', 'Created On', 'Last Modified'])
            for data_value in itertools.chain(round_data.group_data_value_set.all(),
                                              round_data.participant_data_value_set.all()):
                writer.writerow([data_value.owner, round_configuration, data_value.parameter.label,
                                 data_value.value, data_value.date_created, data_value.last_modified])
                # write out all chat messages as a side bar
            chat_messages = ChatMessage.objects.filter(round_data=round_data)
            if chat_messages.count() > 0:
                # sort by group first, then time
                writer.writerow(['Chat Messages'])
                writer.writerow(
                    ['Group', 'Participant', 'Message', 'Time', 'Round'])
                for chat_message in chat_messages.order_by('participant_group_relationship__group', 'date_created'):
                    writer.writerow([chat_message.group, chat_message.participant, chat_message.message,
                                     chat_message.date_created, round_configuration])


@group_required(PermissionGroup.experimenter)
@ownership_required(Experiment)
@require_GET
def export_configuration(request, pk=None, file_extension='.xml'):
    experiment = get_object_or_404(Experiment, pk=pk)
    content_type = mimetypes.types_map[file_extension]
    response = HttpResponse(content_type=content_type)
    response[
        'Content-Disposition'] = 'attachment; filename=%s' % experiment.configuration_file_name(file_extension)
    experiment.experiment_configuration.serialize(stream=response)
    return response


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@ownership_required(Experiment)
@require_GET
def download_participants(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename=participants.csv'
    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(['Email', 'Password', 'URL'])
    full_participant_url = experiment.full_participant_url
    authentication_code = experiment.authentication_code
    for participant in experiment.participant_set.all():
        writer.writerow(
            [participant.email, authentication_code, full_participant_url])
    return response


# FIXME: add data converter objects to write to csv, excel, etc.
@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@require_GET
@ownership_required(Experiment)
def download_data(request, pk=None, file_type='csv'):
    experiment = get_object_or_404(Experiment.objects.select_related('experimenter'), pk=pk)
    content_type = mimetypes.types_map['.%s' % file_type]
    logger.debug("Downloading data as %s", content_type)
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name()
    writer = unicodecsv.writer(response, encoding='utf-8')
    """ header for group membership, session id, and base participant data """
    writer.writerow(['Group ID', 'Group Number', 'Group Cluster ID', 'Session ID', 'Participant ID', 'Participant Email'])
    group_to_cluster_dict = defaultdict(str)
    for group_cluster in experiment.group_cluster_set.all():
        for g in group_cluster.group_relationship_set.select_related('group').values_list('group', flat=True):
            group_to_cluster_dict[g] = group_cluster.pk

    for group in experiment.group_set.order_by('pk').all():
        for pgr in group.participant_group_relationship_set.select_related('participant__user').all():
            writer.writerow([group.pk, group.number, group_to_cluster_dict[group.pk], group.session_id, pgr.pk,
                             pgr.participant.email])
    """ header for participant data values, chat messages, and per-group data ordered per-round"""
    writer.writerow(
        ['Round', 'Participant ID', 'Participant Number', 'Group ID', 'Parameter', 'Value',
         'Creation Date', 'Creation Time', 'Last Modified Date', 'Last Modified Time'])
    lookup_table_parameters = set()
    for round_data in experiment.round_data_set.select_related('round_configuration').all():
        round_number = round_data.round_number
        # emit experimenter notes
        if round_data.experimenter_notes:
            writer.writerow(
                [round_number, experiment.experimenter.email, '', '', 'Experimenter Notes',
                 round_data.experimenter_notes, '', '', '', ''])
        # emit all participant data values
        for data_value in round_data.participant_data_value_set.select_related('participant_group_relationship__group',
                                                                               'parameter').all():
            pgr = data_value.participant_group_relationship
            if data_value.parameter.is_foreign_key:
                lookup_table_parameters.add(data_value.parameter)
            dc = data_value.date_created
            lm = data_value.last_modified
            writer.writerow(
                [round_number, pgr.pk, pgr.participant_number, pgr.group.pk, data_value.parameter.label,
                 data_value.value, dc.date(), dc.time(), lm.date(), lm.time()])
            # emit all chat messages
        chat_messages = ChatMessage.objects.filter(round_data=round_data)
        if chat_messages.count() > 0:
            for chat_message in chat_messages.order_by('participant_group_relationship__group', 'date_created'):
                pgr = chat_message.participant_group_relationship
                dc = chat_message.date_created
                lm = chat_message.last_modified
                writer.writerow([round_number, pgr.pk, pgr.participant_number, pgr.group.pk, "Chat Message",
                                 chat_message.string_value, dc.date(), dc.time(), lm.date(), lm.time()])
        # emit group round data values
        for data_value in round_data.group_data_value_set.select_related('group').all():
            dc = data_value.date_created
            lm = data_value.last_modified
            writer.writerow([round_number, '', '', data_value.group.pk, data_value.parameter.label,
                             data_value.value, dc.date(), dc.time(), lm.date(), lm.time()])
    if lookup_table_parameters:
        writer.writerow(['Lookup Tables'])
        for ltp in lookup_table_parameters:
            model = ltp.get_model_class()
            # introspect on the model and emit all of its relevant fields
            data_fields = get_model_fields(model)
            data_field_names = itertools.chain(
                ['Type', 'ID'], [f.verbose_name for f in data_fields])
            writer.writerow(data_field_names)
            for obj in model.objects.order_by('pk').all():
                writer.writerow(itertools.chain(
                    [model.__name__, obj.pk], [getattr(obj, f.name) for f in data_fields]))
    return response


@group_required(PermissionGroup.experimenter)
@ownership_required(Experiment)
@require_GET
def download_data_excel(request, pk=None):
    import xlwt

    try:
        experiment = Experiment.objects.get(pk=pk)
        response = HttpResponse(mimetype='application/vnd.ms-excel')
        response[
            'Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name(file_ext='xls')
        workbook = xlwt.Workbook()
        group_sheet = workbook.add_sheet('Group Data')
        current_row = 0
        group_sheet.write(0, 0, 'Group')
        group_sheet.write(0, 1, 'Participant')
        for group in experiment.group_set.all():
            for participant in group.participant_set.all():
                group_sheet.write(current_row, 0, group)
                group_sheet.write(current_row, 1, participant)
            current_row += 1
        group_sheet.write(current_row, 0, 'Group')
        group_sheet.write(current_row, 1, 'Round')
        group_sheet.write(current_row, 2, 'Data Parameter')
        group_sheet.write(current_row, 3, 'Data Parameter Value')
        for group in experiment.group_set.all():
            for data_value in group.data_value_set.all():
                group_sheet.write(current_row, 0, group)
                group_sheet.write(
                    current_row, 1, data_value.round_configuration)
                group_sheet.write(current_row, 2, data_value.parameter.label)
                group_sheet.write(current_row, 3, data_value.value)
            current_row += 1

        participant_sheet = workbook.add_sheet('Participant Data')
        current_row = 0
        participant_sheet.write(0, 0, 'Participant')
        participant_sheet.write(0, 1, 'Data Parameter')
        participant_sheet.write(0, 2, 'Data Parameter Value')
        raise NotImplementedError("Not finished")
    except Experiment.DoesNotExist as e:
        logger.warning(e)


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@require_POST
def update_experiment(request):
    form = UpdateExperimentForm(request.POST or None)
    if form.is_valid():
        experimenter = request.user.experimenter
        experiment = get_object_or_404(Experiment.objects.select_related('experimenter'),
                                       pk=form.cleaned_data['experiment_id'],
                                       experimenter=experimenter)
        action = form.cleaned_data['action']
        logger.debug("experimenter %s invoking %s on %s", experimenter, action, experiment)
        try:
            response_tuples = experiment.invoke(action, experimenter)
            logger.debug("experiment.invoke %s -> %s", action, str(response_tuples))
            logger.debug("Publishing to redis on channel experimenter_channel.{}".format(experiment.pk))
# FIXME: remove duplication here + update_participants
            experiment.notify_participants(create_message_event("", "update"))
            experiment.notify_experimenter(create_message_event("Updating all connected participants"))
            return JsonResponse({
                'success': True,
                'experiment': experiment.to_dict(include_round_data=True)
            })
        except AttributeError as e:
            logger.warning("no attribute %s on experiment %s (%s)", action, experiment.status_line, e)
    return JsonResponse({
        'success': False,
        'message': 'Invalid update experiment request: %s' % form
    })


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
@require_POST
def update_participants(request, pk):
    try:
        experiment = Experiment.objects.get(pk=pk)
        logger.debug("Publishing to redis on channel experimenter_channel.{}".format(experiment.pk))
# FIXME: remove duplication here + update_participants
        experiment.notify_participants(create_message_event("", "update"))
        experiment.notify_experimenter(create_message_event("Updating all connected participants"))
        return JsonResponse(SUCCESS_DICT)
    except Exception as e:
        logger.debug(e)
        return JsonResponse(FAILURE_DICT)


@group_required(PermissionGroup.participant)
@require_GET
def completed_survey(request):
    pgr_id = request.GET.get('pid', None)
    # FIXME: prevent manual pinging (check referrer + threaded data sent to
    # the quiz and passed back)
    logger.debug("http referer: %s", request.META.get('HTTP_REFERER'))
    success = False
    try:
        if pgr_id and pgr_id.isdigit():
            pgr = get_object_or_404(ParticipantGroupRelationship, pk=pgr_id)
        else:
            # no incoming pid, try to look it up for the given logged in user
            participant = request.user.participant
            # FIXME: create a ParticipantGroupRelationship.objects.active
            # QuerySet method?
            pgr = ParticipantGroupRelationship.objects.get(group__experiment=get_active_experiment(participant),
                                                           participant=participant)
        pgr.survey_completed = True
        pgr.save()
        success = True
    except ParticipantGroupRelationship.DoesNotExist:
        logger.debug("no ParticipantGroupRelationship found with id %s", pgr_id)
    return JsonResponse({'success': success})


@group_required(PermissionGroup.participant)
def check_survey_completed(request, pk=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=pk)
    return JsonResponse({
        'survey_completed': experiment.get_participant_group_relationship(participant).survey_completed,
    })


def get_cas_user(tree):
    """
    Callback invoked by the CAS module that ensures that the user signing in via CAS has a valid Django User associated
    with them. Primary responsibility is to create a Django User / Participant if none existed, or to associate the CAS
    login id with the given User. This needs to be done *before* the CAS module creates a User object so that we don't
    end up creating duplicate users with a different username and the same email address.

    1. If no Django user exists with the given username (institutional username), get details from the ASU web directory
    (FIXME: this is brittle and specific to ASU, will need to update if we ever roll CAS login out for other
    institutions) and populate a Django user / vcweb Participant with those details
    2. If a Django user does exist with the given institutional username (e.g., asurite) there are a few corner cases to
    consider:
    a. the account could have been created before CAS was implemented, so there is no institutional username set (or
    it's set to the email address instead of the ASURITE id). In this case we need to set the username to
    the ASURITE id
    b. easy case, the account was created via CAS and all the fields are correct

    To make it working for any specific institution you'll need to change the CAS settings in the settings.py file

    Following settings are important and required by the VCWEB and are university specific

    1. CAS_UNIVERSITY_NAME - Institutional CAS provider name
    2. CAS_UNIVERSITY_URL - Institutional CAS provider URL
    3. WEB_DIRECTORY_URL - Web directory service URL providing basic user details based on institutional username
    4. CAS_SERVER_URL - CAS URL provided by the institution to centrally authenticate users
    5. CAS_REDIRECT_URL - The relative url where the user should be re-directed after successful authentication
    6. CAS_RESPONSE_CALLBACKS - Callback invoked after successful authentication by CAS
    """
    username = tree[0][0].text.lower()
    logger.debug("cas tree: %s", tree)
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = create_cas_participant(username, tree)
    if user:
        set_authentication_token(user, uuid.uuid4().hex)
    return user


def create_cas_participant(username, cas_tree):
    # If this exception is thrown it means that User Logged in via CAS is a new user
    logger.debug("No user found with username %s", username)
    return create_cas_user_and_assign_group(username=username)


def create_cas_user_and_assign_group(username, first_name=None, last_name=None, email=None, major=None):
    institution = Institution.objects.get(name=settings.CAS_UNIVERSITY_NAME)
    if first_name:
        user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email)
        participant = Participant.objects.create(user=user, major=major,
                                                 institution=institution, can_receive_invitations=True)
    else:
        user = User.objects.create_user(username=username)
        participant = Participant.objects.create(user=user, institution=institution, can_receive_invitations=True)
    logger.debug("CAS backend created participant %s from web directory", participant)
    password = User.objects.make_random_password()
    user.set_password(password)
    # Assign the user to participant permission group
    user.groups.add(PermissionGroup.participant.get_django_group())
    user.save()
    return user


@group_required(PermissionGroup.experimenter)
@require_POST
def update_experiment_param_value(request, pk):
    form = ExperimentParameterValueForm(request.POST or None, pk=pk)
    if form.is_valid():
        epv = form.save()
        return JsonResponse({'success': True, 'experiment_param': epv.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@require_POST
def update_round_param_value(request, pk):
    form = RoundParameterValueForm(request.POST or None, pk=pk)
    if form.is_valid():
        rpv = form.save()
        return JsonResponse({'success': True, 'round_param': rpv.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@require_POST
def update_round_configuration(request, pk):
    form = RoundConfigurationForm(request.POST or None, pk=pk)
    if form.is_valid():
        rc = form.save()
        return JsonResponse({'success': True, 'round_config': rc.to_dict()})
    return JsonResponse({'success': False, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentConfiguration)
@require_POST
def update_experiment_configuration(request, pk):
    form = ExperimentConfigurationForm(request.POST or None, pk=pk)
    if form.is_valid():
        ec = form.save()
        logger.debug("updated experiment configuration: %s", ec)
        return JsonResponse(SUCCESS_DICT)
    return JsonResponse({'success': False, 'errors': form.errors})


# FIXME : Merge delete experiment config in update experiment
@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentConfiguration)
def delete_experiment_configuration(request, pk):
    try:
        ExperimentConfiguration.objects.get(pk=pk).delete()
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '%s (%s)' % (e.message, type(e))
        })

    return JsonResponse(SUCCESS_DICT)


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
# @ownership_required(ExperimentConfiguration)
@require_GET
def show_experiment_configuration(request, pk):
    ec = get_object_or_404(ExperimentConfiguration, pk=pk)
    ecf = ExperimentConfigurationForm(instance=ec)

    json_data = get_experiment_configuration_json_data(ec)

    return render(request, 'experimenter/show-configuration.html', {
        'json_data': dumps(json_data),
        'experiment_config_form': ecf,
    })


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentConfiguration)
@require_GET
def edit_experiment_configuration(request, pk):
    ec = ExperimentConfiguration.objects.get(pk=pk)
    ecf = ExperimentConfigurationForm(instance=ec)

    json_data = get_experiment_configuration_json_data(ec)

    return render(request, 'experimenter/edit-configuration.html', {
        'json_data': dumps(json_data),
        'experiment_config': ec,
        'experiment_config_form': ecf,
        'round_config_form': RoundConfigurationForm(),
        'round_param_form': RoundParameterValueForm(),
        'exp_param_form': ExperimentParameterValueForm(),
    })


def get_experiment_configuration_json_data(ec):
    # FIXME: replace with DRF
    epv = ExperimentParameterValue.objects.select_related('experiment_configuration', 'parameter').filter(
        experiment_configuration=ec)
    exp_param_values_list = [param.to_dict() for param in epv]

    round_config = RoundConfiguration.objects.select_related('experiment_configuration').filter(
        experiment_configuration=ec)
    round_config_list = [r.to_dict() for r in round_config]

    round_param_values = RoundParameterValue.objects.select_related('round_configuration', 'parameter').filter(
        round_configuration__in=round_config)
    round_param_values_list = [round_param.to_dict() for round_param in round_param_values]

    # Get the round parameter values for each round
    for round_configuration in round_config_list:
        round_configuration["children"] = []
        for param in round_param_values_list:
            if round_configuration['pk'] == param['round_configuration']:
                # set the round params list as this round's children
                round_configuration["children"].append(param)

    return {
        'expParamValuesList': exp_param_values_list,
        'roundConfigList': round_config_list,
    }


class OstromlabFaqList(ListView):
    model = OstromlabFaqEntry
    context_object_name = 'faq_entries'
    template_name = 'ostromlab/faq.html'


@group_required(PermissionGroup.experimenter)
@require_POST
def clone_experiment_configuration(request):
    experiment_configuration_id = request.POST.get('experiment_configuration_id')
    logger.debug("cloning experiment configuration %s", experiment_configuration_id)
    experiment_configuration = get_object_or_404(ExperimentConfiguration, pk=experiment_configuration_id)
    experimenter = request.user.experimenter
    cloned_experiment_configuration = experiment_configuration.clone(creator=experimenter)
    return JsonResponse({'success': True, 'experiment_configuration': cloned_experiment_configuration.to_dict()})


@login_required
@group_required(PermissionGroup.participant)
def unsubscribe(request):
    user = request.user
    if is_participant(user) and user.participant.can_receive_invitations:
        successfully_unsubscribed = False
        if request.method == "POST":
            user.is_active = False
            user.save()
            participant = user.participant
            participant.can_receive_invitations = False
            participant.save()
            successfully_unsubscribed = True
            logger.debug("unsubscribing user %s", user)
        return render(request, 'accounts/unsubscribe.html', {'successfully_unsubscribed': successfully_unsubscribed})
    return render(request, 'invalid_request.html',
                  {'message': "You aren't currently subscribed to our experiment session mailing list."})


class AntiSpamContactFormView(ContactFormView):
    form_class = AntiSpamContactForm

    def form_valid(self, form):
        return super(AntiSpamContactFormView, self).form_valid(form)


@login_required
@require_GET
@group_required(PermissionGroup.experimenter)
def audit_report(request):
    return render(request, 'admin/audit_report.html', get_audit_data())


# Sets up Autocomplete functionality for Institution Field on Participant
# Account Profile
class InstitutionAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if self.q:
            return Institution.objects.filter(models.Q(name__istartswith=self.q) |
                                              models.Q(acronym__istartswith=self.q))
        return Institution.objects.all()


# Sets up autocomplete functionality for major field on participant account profile
class ParticipantMajorAutocomplete(autocomplete.Select2ListView):
    def create(self, text):
        logger.debug("Creating major %s", text)
        pass

    def get_list(self):
        qs = Participant.objects.order_by('major').distinct('major')
        if self.q:
            qs = qs.filter(major__istartswith=self.q)
        return list(qs.values_list('major', flat=True))
