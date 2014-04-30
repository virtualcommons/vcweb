from collections import defaultdict
from datetime import datetime, time, timedelta
from time import mktime
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.http import HttpResponse
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.template import Context
from django.template.loader import get_template
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, TemplateView, ListView
from django.views.generic.detail import SingleObjectMixin
from django.forms.models import modelformset_factory
from vcweb.core import dumps
from vcweb.core.http import JsonResponse
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required, retry
from vcweb.core.forms import (RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm,
                              UpdateExperimentForm, AsuRegistrationForm, ParticipantGroupIdForm,
                              RegisterEmailListParticipantsForm, RegisterTestParticipantsForm,
                              LogMessageForm, BookmarkExperimentMetadataForm, ExperimentConfigurationForm,
                              ExperimentParameterValueForm, RoundConfigurationForm, RoundParameterValuesForm,
                              SessionInviteForm, SessionForm, ParticipantAttendanceForm, CancelSignupForm)
from vcweb.core.models import (User, ChatMessage, Participant, ParticipantExperimentRelationship,
                               ParticipantGroupRelationship, ExperimentConfiguration, ExperimenterRequest, Experiment,
                               Institution, is_participant, is_experimenter, BookmarkedExperimentMetadata,
                               OstromlabFaqEntry, Experimenter, ExperimentParameterValue, RoundConfiguration,
                               RoundParameterValue, Parameter, ParticipantSignup, get_model_fields, ExperimentSession,
                               ExperimentMetadata, Invitation, send_email)
import markdown
import random
import itertools
import logging
import mimetypes
import unicodecsv
import urllib2
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)
mimetypes.init()
SUCCESS_JSON = dumps({'success': True})
FAILURE_JSON = dumps({'success': False})


class AnonymousMixin(object):
    """ provides the anonymous_required decorator """

    @method_decorator(anonymous_required)
    def dispatch(self, *args, **kwargs):
        return super(AnonymousMixin, self).dispatch(*args, **kwargs)


class Participate(TemplateView):
    @method_decorator(participant_required)
    def dispatch(self, *args, **kwargs):
        participant = self.request.user.participant
        experiment = get_active_experiment(participant)
        if experiment is None:
            return redirect('core:dashboard')
        else:
            return redirect(experiment.participant_url)


class DashboardViewModel(object):
    def to_json(self):
        return dumps(self.to_dict())


class ExperimenterDashboardViewModel(DashboardViewModel):
    template_name = 'experimenter/dashboard.html'

    def __init__(self, user):
        self.experimenter = user.experimenter
        _configuration_cache = {}
        self.experiment_metadata_dict = defaultdict(list)
        for ec in ExperimentConfiguration.objects.select_related('experiment_metadata', 'creator'):
            self.experiment_metadata_dict[ec.experiment_metadata].append(ec)
            _configuration_cache[ec.pk] = ec
        self.experiment_metadata_list = []
        bem_pks = BookmarkedExperimentMetadata.objects.filter(experimenter=self.experimenter).values_list(
            'experiment_metadata', flat=True)
        for em, ecs in self.experiment_metadata_dict.iteritems():
            d = em.to_dict(include_configurations=True, configurations=ecs)
            d['bookmarked'] = em.pk in bem_pks
            self.experiment_metadata_list.append(d)

        experiment_status_dict = defaultdict(list)
        for e in Experiment.objects.for_experimenter(self.experimenter).order_by('-pk'):
            e.experiment_configuration = _configuration_cache[e.experiment_configuration.pk]
            experiment_status_dict[e.status].append(
                e.to_dict(attrs=('monitor_url', 'status_line', 'controller_url')))
        self.pending_experiments = experiment_status_dict['INACTIVE']
        self.running_experiments = experiment_status_dict['ACTIVE'] + experiment_status_dict['ROUND_IN_PROGRESS']
        self.archived_experiments = experiment_status_dict['COMPLETED']

    def to_dict(self):
        return {
            'experimentMetadataList': self.experiment_metadata_list,
            'pendingExperiments': self.pending_experiments,
            'runningExperiments': self.running_experiments,
            'archivedExperiments': self.archived_experiments,
        }


class ParticipantDashboardViewModel(DashboardViewModel):
    template_name = 'participant/dashboard.html'

    def __init__(self, user):
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
            'hasPendingInvitations': self.participant.has_pending_invitations,
            'signups': self.signups,
            'showEndDates': self.show_end_dates,
        }


class DashboardViewModelFactory(object):
    @staticmethod
    def create(user):
        if user is None or not user.is_active:
            logger.error("can't create dashboard view model from invalid user %s", user)
            raise ValueError("invalid user")
        if is_experimenter(user):
            return ExperimenterDashboardViewModel(user)
        else:
            return ParticipantDashboardViewModel(user)


@login_required
def dashboard(request):
    """
    selects the appropriate dashboard template and data for participants and experimenters
    """
    user = request.user
    if is_participant(user):
        if not user.participant.is_profile_complete:
            return redirect('core:profile')
        elif user.participant.has_pending_invitations:
            return redirect('subject_pool:experiment_session_signup')

    dashboard_view_model = DashboardViewModelFactory.create(user)
    return render(request, dashboard_view_model.template_name,
                  {'dashboardViewModelJson': dashboard_view_model.to_json()})


@login_required
def cas_asu_registration(request):
    user = request.user
    if is_participant(user) and not user.participant.is_profile_complete:
        directory_profile = ASUWebDirectoryProfile(user.username)
        logger.debug("directory profile: %s", directory_profile)
        # user.save()
        return render(request, 'account/asu_registration.html',
                      {'form': AsuRegistrationForm(instance=user.participant)})
    else:
        return redirect('core:dashboard')


@participant_required
def cas_asu_registration_submit(request):
    form = AsuRegistrationForm(request.POST or None)
    if form.is_valid():
        user = request.user
        participant = user.participant
        user.email = form.cleaned_data['email'].lower()
        participant.can_receive_invitations = True
        for attr in ('gender', 'favorite_color', 'favorite_movie_genre', 'class_status', 'favorite_sport',
                     'favorite_food', 'class_status', 'major',):
            setattr(participant, attr, form.cleaned_data.get(attr))
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()
        participant.save()
        messages.add_message(request, messages.INFO,
                             _("You've been successfully registered with our mailing list. Thanks!"))
        logger.debug("created new participant from asurite registration: %s", participant)
        return redirect('core:dashboard')
    else:
        return redirect('core:cas_asu_registration')


@login_required
def get_dashboard_view_model(request):
    return JsonResponse(
        dumps({'success': True, 'dashboardViewModelJson': DashboardViewModelFactory.create(request.user).to_json()}))


def set_authentication_token(user, authentication_token=''):
    commons_user = None
    if is_participant(user):
        commons_user = user.participant
    elif is_experimenter(user):
        commons_user = user.experimenter
    else:
        logger.error("Invalid user: %s", user)
        return
    logger.debug("%s authentication_token=%s", commons_user, authentication_token)
    commons_user.authentication_token = authentication_token
    commons_user.save()


def get_active_experiment(participant, experiment_metadata=None, **kwargs):
    pers = []
    if experiment_metadata is not None:
        pers = ParticipantExperimentRelationship.objects.active(participant=participant,
                                                                experiment__experiment_metadata=experiment_metadata,
                                                                **kwargs)
    else:
        pers = ParticipantExperimentRelationship.objects.active(participant=participant, **kwargs)
    if pers:
        logger.debug("using first active experiment %s for participant %s", pers[0], participant)
        return pers[0].experiment
    return None


def autocomplete_account(request, term):
    candidates = []
    if term in ('major', 'institution'):
        candidates = ["Implement", "Me"]
        return JsonResponse(dumps({'success': True, 'candidates': candidates}))
    else:
        logger.debug("can't autocomplete unsupported term %s", term)
        return JsonResponse(dumps({'success': False, 'message': "Unsupported autocomplete term %s" % term}))


def api_logout(request):
    user = request.user
    set_authentication_token(user)
    auth.logout(request)
    return JsonResponse(SUCCESS_JSON)


def participant_api_login(request):
    # FIXME: assumes participant login
    form = LoginForm(request.POST or None)
    try:
        if form.is_valid():
            user = form.user_cache
            logger.debug("user was authenticated as %s, attempting to login", user)
            auth.login(request, user)
            set_authentication_token(user, request.session.session_key)
            participant = user.participant
            # FIXME: defaulting to first active experiment... need to revisit this.
            active_experiment = get_active_experiment(participant)
            participant_group_relationship = active_experiment.get_participant_group_relationship(participant)
            return JsonResponse(dumps({'success': True, 'participant_group_id': participant_group_relationship.pk}))
        else:
            logger.debug("invalid form %s", form)
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return JsonResponse(dumps({'success': False, 'message': "Invalid login"}))


class LoginView(FormView, AnonymousMixin):
    form_class = LoginForm
    template_name = 'account/login.html'

    def form_valid(self, form):
        request = self.request
        user = form.user_cache
        auth.login(request, user)
        set_authentication_token(user, request.session.session_key)
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        return_url = self.request.GET.get('next')
        user = self.request.user
        success_url = reverse('core:dashboard')
        if is_participant(user):
            participant = self.request.user.participant
            active_experiment = get_active_experiment(participant)
            if active_experiment:
                success_url = active_experiment.participant_url
        return return_url if return_url else success_url


class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        user = request.user
        set_authentication_token(user)
        auth.logout(request)
        return redirect('home')


class RegistrationView(FormView, AnonymousMixin):
    form_class = RegistrationForm
    template_name = 'account/register.html'

    def form_valid(self, form):
        email = form.cleaned_data['email'].lower()
        password = form.cleaned_data['password']
        first_name = form.cleaned_data['first_name']
        last_name = form.cleaned_data['last_name']
        institution_string = form.cleaned_data['institution']
        experimenter_requested = form.cleaned_data['experimenter']
        institution, created = Institution.objects.get_or_create(name=institution_string)
        user = User.objects.create_user(email, email, password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        if experimenter_requested:
            experimenter_request = ExperimenterRequest.objects.create(user=user)
            logger.debug("creating new experimenter request: %s", experimenter_request)
        participant = Participant.objects.create(user=user, institution=institution)
        logger.debug("Creating new participant: %s", participant)
        request = self.request
        auth.login(request, auth.authenticate(username=email, password=password))
        set_authentication_token(user, request.session.session_key)
        # FIXME: disabling auto registration, experiment configuration flags are not being set properly
        #        for experiment in Experiment.objects.public():
        #            experiment.add_participant(participant)
        return super(RegistrationView, self).form_valid(form)

    def get_success_url(self):
        return reverse('core:dashboard')


class AccountView(FormView):
    pass


@login_required
def update_account_profile(request):
    user = request.user

    if is_experimenter(user):
        form = ExperimenterAccountForm(request.POST or None)
        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            institution = form.cleaned_data.get('institution')
            e = Experimenter.objects.get(pk=user.experimenter.pk)

            if institution:
                ins, created = Institution.objects.get_or_create(name=institution)
                e.institution = ins
            else:
                e.institution = None
                logger.debug('Institution is empty')

            if e.user.email != email:
                users = User.objects.filter(email=email)
                if users.count() > 0:
                    return JsonResponse(dumps({
                        'success': False,
                        'message': 'This email is already registered with our system, please try another.'
                    }))

            for attr in ('first_name', 'last_name', 'email'):
                setattr(e.user, attr, form.cleaned_data.get(attr))

            e.save()
            e.user.save()

            return JsonResponse(dumps({
                'success': True,
                'message': 'Profile updated successfully.'
            }))
        return JsonResponse(dumps({'success': False,
                                   'message': 'Something went wrong. Please try again.'}))

    else:
        form = ParticipantAccountForm(request.POST or None)

        if form.is_valid():
            email = form.cleaned_data.get('email').lower()
            institution = form.cleaned_data.get('institution')

            p = Participant.objects.get(pk=user.participant.pk)

            if institution:
                ins, created = Institution.objects.get_or_create(name=institution)
                p.institution = ins
            else:
                p.institution = None
                logger.debug('Institution is empty')

            if p.user.email != email:
                users = User.objects.filter(email=email)
                if users.count() > 0:
                    return JsonResponse(dumps({
                        'success': False,
                        'message': 'This email is already registered with our system, please try another.'
                    }))

            for attr in (
                    'major', 'class_status', 'gender', 'can_receive_invitations', 'favorite_food', 'favorite_sport',
                    'favorite_color', 'favorite_movie_genre'):
                setattr(p, attr, form.cleaned_data.get(attr))

            for attr in ('first_name', 'last_name', 'email'):
                setattr(p.user, attr, form.cleaned_data.get(attr))

            p.save()
            p.user.save()

            return JsonResponse(dumps({
                'success': True,
                'message': 'Updated profile successfully.'
            }))

        return JsonResponse(dumps({'success': False,
                                   'message': 'You need to provide your major, class status, gender, favorite sport, '
                                              'favorite food, favorite color and favorite movie genre, if you want to '
                                              'receive invitations'}))


@login_required
def check_user_email(request):
    email = request.GET.get("email").lower()
    current_user = request.user
    success = False
    if current_user.email != email:
        users = User.objects.filter(email=email)
        success = users.count() == 0
    else:
        success = True
    return JsonResponse(dumps(success))


@login_required
def account_profile(request):
    user = request.user
    if is_participant(user):
        form = ParticipantAccountForm(instance=user.participant)
        # logger.debug(form)
    else:
        form = ExperimenterAccountForm(instance=user.experimenter)
    return render(request, 'account/profile.html', {'form': form})


''' participant views '''


class ParticipantMixin(object):
    @method_decorator(participant_required)
    def dispatch(self, *args, **kwargs):
        return super(ParticipantMixin, self).dispatch(*args, **kwargs)


"""
experimenter views
FIXME: add has_perms authorization to ensure that only experimenters can access
these.
"""


class ExperimenterMixin(object):
    @method_decorator(experimenter_required)
    def dispatch(self, *args, **kwargs):
        return super(ExperimenterMixin, self).dispatch(*args, **kwargs)


class SingleExperimentMixin(SingleObjectMixin):
    model = Experiment
    context_object_name = 'experiment'

    # FIXME: is this the right place for this?  Useful when a form mixes this class in.
    def get_initial(self):
        self.object = self.get_object()
        return {"experiment_pk": self.object.pk}

    def process(self):
        pass

    def can_access_experiment(self, user, experiment):
        return True

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk', None)
        experiment = get_object_or_404(
            Experiment.objects.select_related('experiment_metadata', 'experiment_configuration', 'experimenter'), pk=pk)
        user = self.request.user
        if self.can_access_experiment(user, experiment):
            return experiment
        else:
            logger.warning("unauthorized access by user %s to experiment %s", user, experiment)
            raise PermissionDenied("You do not have access to %s" % experiment)


class ParticipantSingleExperimentMixin(SingleExperimentMixin, ParticipantMixin):
    def can_access_experiment(self, user, experiment):
        return experiment.participant_set.filter(participant__user=user).count() == 1


class ExperimenterSingleExperimentMixin(SingleExperimentMixin, ExperimenterMixin):
    def can_access_experiment(self, user, experiment):
        return is_experimenter(user, experiment.experimenter)


class ExperimenterSingleExperimentView(ExperimenterSingleExperimentMixin, TemplateView):
    def get(self, request, **kwargs):
        self.experiment = self.object = self.get_object()
        self.process()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)


@experimenter_required
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
            return JsonResponse(SUCCESS_JSON)
        else:
            logger.warn("Invalid toggle bookmark experiment metadata request: %s", request)
    return JsonResponse(FAILURE_JSON)


@experimenter_required
def monitor(request, pk=None):
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_configuration', 'experimenter'), pk=pk)
    user = request.user
    if is_experimenter(user, experiment.experimenter):
        return render(request, 'experimenter/monitor.html', {
            'experiment': experiment,
            'experimentModelJson': experiment.to_json(include_round_data=True),
        })
    else:
        logger.warning("unauthorized access to experiment %s by user %s", experiment, user)
        raise PermissionDenied("You do not have access to %s" % experiment)


class BaseExperimentRegistrationView(ExperimenterSingleExperimentMixin, FormView):
    def get_initial(self):
        _initial = super(BaseExperimentRegistrationView, self).get_initial()
        experiment = self.object
        _initial.update(
            registration_email_from_address=experiment.experimenter.email,
            experiment_password=experiment.authentication_code,
            registration_email_subject=experiment.registration_email_subject,
            registration_email_text=experiment.registration_email_text
        )
        return _initial

    def form_valid(self, form):
        experiment = self.object
        experiment.authentication_code = form.cleaned_data.get('experiment_password')
        for field in ('start_date', 'registration_email_subject', 'registration_email_text'):
            setattr(experiment, field, form.cleaned_data.get(field))
        experiment.save()
        return super(BaseExperimentRegistrationView, self).form_valid(form)

    def get_success_url(self):
        return reverse('core:monitor_experiment', kwargs={'pk': self.object.pk})


class RegisterEmailListView(BaseExperimentRegistrationView):
    form_class = RegisterEmailListParticipantsForm
    template_name = 'experimenter/register-email-participants.html'

    def form_valid(self, form):
        valid = super(RegisterEmailListView, self).form_valid(form)
        emails = form.cleaned_data.get('participant_emails')
        institution = form.cleaned_data.get('institution')
        sender = form.cleaned_data.get('sender')
        from_email = form.cleaned_data.get('registration_email_from_address')
        experiment = self.object
        logger.debug("registering participants %s at institution %s for experiment: %s", emails, institution,
                     experiment)
        experiment.register_participants(emails=emails, institution=institution,
                                         password=experiment.authentication_code,
                                         sender=sender, from_email=from_email)
        return valid


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
            experiment = self.object
            experiment.setup_test_participants(count=number_of_participants,
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
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name(file_ext=file_ext)
        self.export_data(response, experiment)
        return response


class CsvDataExporter(DataExportMixin):
    def export_data(self, response, experiment):
        writer = unicodecsv.writer(response, encoding='utf-8')
        writer.writerow(['Group', 'Members'])
        for group in experiment.group_set.all():
            writer.writerow(itertools.chain.from_iterable([[group], group.participant_set.all()]))
        for round_data in experiment.round_data_set.all():
            round_configuration = round_data.round_configuration
            # write out group-wide and participant data values
            writer.writerow(['Owner', 'Round', 'Data Parameter', 'Data Parameter Value', 'Created On', 'Last Modified'])
            for data_value in itertools.chain(round_data.group_data_value_set.all(),
                                              round_data.participant_data_value_set.all()):
                writer.writerow([data_value.owner, round_configuration, data_value.parameter.label,
                                 data_value.value, data_value.date_created, data_value.last_modified])
                # write out all chat messages as a side bar
            chat_messages = ChatMessage.objects.filter(round_data=round_data)
            if chat_messages.count() > 0:
                # sort by group first, then time
                writer.writerow(['Chat Messages'])
                writer.writerow(['Group', 'Participant', 'Message', 'Time', 'Round'])
                for chat_message in chat_messages.order_by('participant_group_relationship__group', 'date_created'):
                    writer.writerow([chat_message.group, chat_message.participant, chat_message.message,
                                     chat_message.date_created, round_configuration])


@experimenter_required
def export_configuration(request, pk=None, file_extension='.xml'):
    experiment = get_object_or_404(Experiment, pk=pk)
    if experiment.experimenter != request.user.experimenter:
        logger.warning("unauthorized access to %s by %s", experiment, request.user.experimenter)
        raise PermissionDenied("You don't appear to have access to this experiment.")
    content_type = mimetypes.types_map[file_extension]
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % experiment.configuration_file_name(file_extension)
    experiment.experiment_configuration.serialize(stream=response)
    return response


@experimenter_required
def download_participants(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    if experiment.experimenter != request.user.experimenter:
        logger.error("unauthorized access to %s from %s", experiment, request.user.experimenter)
        raise PermissionDenied("You don't have access to this experiment.")
    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename=participants.csv'
    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(['Email', 'Password', 'URL'])
    full_participant_url = experiment.full_participant_url
    authentication_code = experiment.authentication_code
    for participant in experiment.participant_set.all():
        writer.writerow([participant.email, authentication_code, full_participant_url])
    return response


# FIXME: add data converter objects to write to csv, excel, etc.
@experimenter_required
def download_data(request, pk=None, file_type='csv'):
    experiment = get_object_or_404(Experiment, pk=pk)
    if experiment.experimenter != request.user.experimenter:
        logger.warning("unauthorized access to %s from %s", experiment, request.user.experimenter)
        raise PermissionDenied("You don't have access to this experiment")
    content_type = mimetypes.types_map['.%s' % file_type]
    logger.debug("Downloading data as %s", content_type)
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name()
    writer = unicodecsv.writer(response, encoding='utf-8')
    """ header for group membership, session id, and base participant data """
    writer.writerow(['Group ID', 'Group Number', 'Session ID', 'Participant ID', 'Participant Email'])
    for group in experiment.group_set.order_by('pk').all():
        for pgr in group.participant_group_relationship_set.select_related('participant__user').all():
            writer.writerow([group.pk, group.number, group.session_id, pgr.pk, pgr.participant.email])
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
                [round_number, 'Experimenter Notes', '', '', 'Experimenter Notes', round_data.experimenter_notes, '',
                 '', '', ''])
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
                 data_value.value, dc.date(), dc.time(), lm.date(), lm.time()
                ])
            # emit all chat messages
        chat_messages = ChatMessage.objects.filter(round_data=round_data)
        if chat_messages.count() > 0:
            for chat_message in chat_messages.order_by('participant_group_relationship__group', 'date_created'):
                pgr = chat_message.participant_group_relationship
                dc = chat_message.date_created
                lm = chat_message.last_modified
                writer.writerow([round_number, pgr.pk, pgr.participant_number, pgr.group.pk, "Chat Message",
                                 chat_message.string_value, dc.date(), dc.time(), lm.date(), lm.time()])
                # emit round data for the group as a whole
        for data_value in round_data.group_data_value_set.select_related('group').all():
            dc = data_value.date_created
            lm = data_value.last_modified
            writer.writerow([round_number, '', '', data_value.group.pk, data_value.parameter.label,
                             data_value.value, dc.date(), dc.time(), lm.date(), lm.time()])
    logger.debug("lookup table parameters: %s", lookup_table_parameters)
    if lookup_table_parameters:
        writer.writerow(['Lookup Tables'])
        for ltp in lookup_table_parameters:
            model = ltp.get_model_class()
            # introspect on the model and emit all of its relevant fields
            data_fields = get_model_fields(model)
            data_field_names = itertools.chain(['Type', 'ID'], [f.verbose_name for f in data_fields])
            writer.writerow(data_field_names)
            for obj in model.objects.order_by('pk').all():
                writer.writerow(itertools.chain([model.__name__, obj.pk], [getattr(obj, f.name) for f in data_fields]))
    return response


@experimenter_required
def download_data_excel(request, pk=None):
    import xlwt

    try:
        experiment = Experiment.objects.get(pk=pk)
        response = HttpResponse(mimetype='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name(file_ext='xls')
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
                group_sheet.write(current_row, 1, data_value.round_configuration)
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


@experimenter_required
def deactivate(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    experimenter = request.user.experimenter
    if experimenter == experiment.experimenter:
        experiment.deactivate()
        return redirect('core:monitor_experiment', pk=pk)
    logger.warning("Invalid experiment deactivation request for %s by %s", experiment, experimenter)
    return redirect('core:dashboard')


@experimenter_required
def update_experiment(request):
    form = UpdateExperimentForm(request.POST or None)
    if form.is_valid():
        experiment = get_object_or_404(Experiment, pk=form.cleaned_data['experiment_id'])
        action = form.cleaned_data['action']
        experimenter = request.user.experimenter
        logger.debug("experimenter %s invoking %s on %s", experimenter, action, experiment)
        try:
            response_tuples = experiment.invoke(action, experimenter)
            logger.debug("invoking action %s: %s", action, str(response_tuples))
            return JsonResponse(dumps({
                'success': True,
                'experiment': experiment.to_dict()
            }))
        except AttributeError as e:
            logger.warning("no attribute %s on experiment %s (%s)", action, experiment.status_line, e)
    return JsonResponse(dumps({
        'success': False,
        'message': 'Invalid update experiment request: %s' % form
    }))


@login_required
def api_logger(request, participant_group_id=None):
    form = LogMessageForm(request.POST or None)
    success = False
    if form.is_valid():
        try:
            participant_group_relationship = ParticipantGroupRelationship.objects.get(pk=participant_group_id)
            level = form.cleaned_data['level']
            message = form.cleaned_data['message']
            logger.log(level, "%s: %s", participant_group_relationship, message)
            success = True
        except ParticipantGroupRelationship.DoesNotExist:
            logger.error("Couldn't locate a participant group relationship for request %s", request)
    else:
        logger.error("Failed to validate log message form %s (%s)", request, form)
    return JsonResponse(dumps({'success': success}))


@participant_required
def completed_survey(request):
    pgr_id = request.GET.get('pid', None)
    # FIXME: prevent manual pinging (check referrer + threaded data sent to the quiz and passed back)
    logger.debug("http referer: %s", request.META.get('HTTP_REFERER'))
    success = False
    try:
        if pgr_id and pgr_id.isdigit():
            pgr = get_object_or_404(ParticipantGroupRelationship, pk=pgr_id)
        else:
            # no incoming pid, try to look it up for the given logged in user
            participant = request.user.participant
            # FIXME: create a ParticipantGroupRelationship.objects.active QuerySet method?
            pgr = ParticipantGroupRelationship.objects.get(group__experiment=get_active_experiment(participant), participant=participant)
        pgr.survey_completed = True
        pgr.save()
        success = True
    except ParticipantGroupRelationship.DoesNotExist as e:
        logger.debug("No ParticipantGroupRelationship found with id %s", pgr_id)
    return JsonResponse(dumps({'success': success}))


@participant_required
def check_survey_completed(request, pk=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=pk)
    return JsonResponse(dumps({
        'survey_completed': experiment.get_participant_group_relationship(participant).survey_completed,
    }))


@participant_required
def participant_ready(request):
    form = ParticipantGroupIdForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data.get('participant_group_id')
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group__experiment'),
                                pk=participant_group_id)
        experiment = pgr.group.experiment
        round_data = experiment.current_round_data
        pgr.set_participant_ready(round_data)
        return JsonResponse(dumps(_ready_participants_dict(experiment)))
    else:
        return JsonResponse(dumps({'success': False, 'message': "Invalid form"}))


def _ready_participants_dict(experiment):
    number_of_ready_participants = experiment.number_of_ready_participants
    all_participants_ready = (number_of_ready_participants == experiment.number_of_participants)
    return {'success': True, 'number_of_ready_participants': number_of_ready_participants,
            'all_participants_ready': all_participants_ready}


@login_required
def check_ready_participants(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    return JsonResponse(dumps(_ready_participants_dict(experiment)))


class ASUWebDirectoryProfile(object):
    """
    A class that encapsulates the complexity of getting the user profile from the WEB Directory
    """

    def __init__(self, username):
        self.username = username
        logger.debug("checking %s", self.profile_url)
        xml_data = self.urlopen_with_retry()
        logger.debug(xml_data)
        parsed = ET.parse(xml_data)
        root = parsed.getroot()
        self.profile_data = root.find('person')
        logger.debug("profile data %s", self.profile_data)

    @retry(urllib2.URLError, tries=3, delay=3, backoff=2, logger=logger)
    def urlopen_with_retry(self):
        return urllib2.urlopen(urllib2.Request(self.profile_url, headers={"Accept": "application/xml"}))

    def __str__(self):
        return "{} {} ({}) (email: {}) (major: {}) (class: {})".format(self.first_name, self.last_name, self.username,
                                                                       self.email, self.major,
                                                                       self.class_status)

    @property
    def profile_url(self):
        return settings.WEB_DIRECTORY_URL + self.username

    @property
    def first_name(self):
        try:
            return self.profile_data.find('firstName').text
        except:
            return None

    @property
    def last_name(self):
        try:
            return self.profile_data.find('lastName').text
        except:
            return None

    @property
    def email(self):
        try:
            return self.profile_data.find('email').text.lower()
        except:
            return None

    @property
    def plans(self):
        try:
            return self.profile_data.find('plans')
        except:
            return None

    @property
    def plan(self):
        try:
            return self.plans.find('plan')
        except:
            return None

    @property
    def major(self):
        try:
            return self.plan.find('acadPlanDescr').text
        except:
            return None

    @property
    def class_status(self):
        try:
            return self.plan.find('acadCareerDescr').text
        except:
            return None

    @property
    def is_undergraduate(self):
        return self.class_status == "Undergraduate"

    @property
    def is_graduate(self):
        return self.class_status == "Graduate"


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

    1. CAS_UNIVERSITY_NAME - The university name of the CAS provider
    2. CAS_UNIVERSITY_URL - The web url of the University
    3. WEB_DIRECTORY_URL - The web Url provided by the university to get the details about the user
    4. CAS_SERVER_URL - The CAS Url used by the university to centrally authorize users
    5. CAS_REDIRECT_URL - The redirect url holds the relative url to which the user should be re-directed by successful authentication
    6. CAS_RESPONSE_CALLBACKS - The call back function that is being called after the successful authentication by CAS
    """
    username = tree[0][0].text.lower()

    try:
        User.objects.get(username=username)
    except ObjectDoesNotExist:
        try:
            directory_profile = ASUWebDirectoryProfile(username)
            logger.debug("found user profile %s (%s)", directory_profile, directory_profile.email)

            user = User.objects.get(username=directory_profile.email)
            user.username = username
            user.save()
        except ObjectDoesNotExist:
            # If this exception is throw it basically means that User Log in via CAS is a new user
            logger.debug("No user found with username %s", username)
            # Create vcweb Participant only if the user is an undergrad student
            if directory_profile.is_undergraduate:
                user = User.objects.create_user(username=username)
                user.first_name = directory_profile.first_name
                user.last_name = directory_profile.last_name
                user.email = directory_profile.email
                logger.debug("%s (%s)", directory_profile, user.email)
                password = User.objects.make_random_password()
                user.set_password(password)
                institution = Institution.objects.get(name='Arizona State University')
                user.save()
                participant = Participant.objects.create(user=user, major=directory_profile.major,
                                                         institution=institution, institution_username=user.username)
                logger.debug("CAS backend created participant %s from web directory", participant)
        except:
            logger.debug("Something went wrong. ASU Web Directory is down")


def reset_password(email, from_email='vcweb@asu.edu', template='registration/password_reset_email.html'):
    form = PasswordResetForm({'email': email})
    if form.is_valid():
        # domain = socket.gethostbyname(socket.gethostname())
        domain = "vcweb.asu.edu"
        return form.save(from_email=from_email, email_template_name=template, domain_override=domain)
    return None


@experimenter_required
def update_experiment_param_value(request, pk):
    form = ExperimentParameterValueForm(request.POST or None)
    request_type = request.POST['request_type']

    if request_type == 'delete':
        epv = ExperimentParameterValue.objects.get(pk=pk).delete()
        return JsonResponse(dumps({
            'success': True
        }))
    if form.is_valid():
        if request_type == 'create':
            epv = ExperimentParameterValue()
            exp_config_pk = request.POST['experiment_configuration']
            epv.experiment_configuration = ExperimentConfiguration.objects.get(pk=exp_config_pk)
        elif request_type == 'update':
            epv = ExperimentParameterValue.objects.get(pk=pk)

        epv.parameter = form.cleaned_data.get('parameter')
        epv.boolean_value = form.cleaned_data.get('boolean_value')
        epv.float_value = form.cleaned_data.get('float_value')
        epv.int_value = form.cleaned_data.get('int_value')
        epv.string_value = form.cleaned_data.get('string_value')
        epv.is_active = form.cleaned_data.get('is_active')

        epv.save()
        return JsonResponse(dumps({
            'success': True,
            'experiment_param': epv.to_dict()
        }))
    else:
        # logger.debug(form._errors)
        # logger.debug(form.non_field_errors())
        return JsonResponse(dumps({
            'success': False,
            'message': form.errors
        }))


@experimenter_required
def update_round_param_value(request, pk):
    form = RoundParameterValuesForm(request.POST or None)
    request_type = request.POST['request_type']

    if request_type == 'delete':
        RoundParameterValue.objects.get(pk=pk).delete()
        return JsonResponse(dumps({
            'success': True
        }))

    if form.is_valid():
        if request_type == 'create':
            rpv = RoundParameterValue()
            round_config_pk = request.POST["round_configuration"]

            try:
                round_config = RoundConfiguration.objects.get(pk=round_config_pk)
                rpv.round_configuration = round_config
            except ObjectDoesNotExist:
                return JsonResponse(dumps({
                    'success': False,
                    'message': "Round Configuration with provided pk does not exist"
                }))
        elif request_type == "update":
            rpv = RoundParameterValue.objects.get(pk=pk)

        rpv.parameter = form.cleaned_data.get('parameter')
        rpv.boolean_value = form.cleaned_data.get('boolean_value')
        rpv.float_value = form.cleaned_data.get('float_value')
        rpv.int_value = form.cleaned_data.get('int_value')
        rpv.string_value = form.cleaned_data.get('string_value')
        rpv.is_active = form.cleaned_data.get('is_active')
        rpv.save()
        return JsonResponse(dumps({
            'success': True,
            'round_param': rpv.to_dict()
        }))
    else:
        # logger.debug(form.errors)
        # logger.debug(form.non_field_errors())
        return JsonResponse(dumps({
            'success': False,
            'message': form.errors
        }))


def sort_round_configurations(old_sequence_number, new_sequence_number, exp_config_pk):
    logger.debug('sorting round configuration sequence numbers')
    round_configs = RoundConfiguration.objects.filter(experiment_configuration__pk=exp_config_pk)
    #logger.debug(round_configs)
    logger.debug(old_sequence_number)
    if old_sequence_number:
        for rc in round_configs:
            current_sequence_number = rc.sequence_number
            if old_sequence_number < current_sequence_number <= new_sequence_number:
                rc.sequence_number = current_sequence_number - 1
                logger.debug('sequence_number decreased by 1')
                rc.save()
            elif new_sequence_number <= current_sequence_number <= old_sequence_number:
                rc.sequence_number = current_sequence_number + 1
                logger.debug('sequence_number increased by 1')
                rc.save()
    else:
        flag = True
        for rc in round_configs:
            current_sequence_number = rc.sequence_number
            if new_sequence_number <= current_sequence_number and flag:
                if new_sequence_number == current_sequence_number:
                    rc.sequence_number = current_sequence_number + 1
                    logger.debug('sequence_number increased by 1')
                    rc.save()
                    new_sequence_number += 1
                else:
                    flag = False


@experimenter_required
def update_round_configuration(request, pk):
    form = RoundConfigurationForm(request.POST or None)
    request_type = request.POST['request_type']
    if request_type == 'delete':
        RoundConfiguration.objects.get(pk=pk).delete()
        return JsonResponse(dumps({
            'success': True
        }))

    if form.is_valid():
        if request_type == 'create':
            rc = RoundConfiguration()
            exp_config_pk = request.POST['experiment_config_pk']
            ec = ExperimentConfiguration.objects.get(pk=exp_config_pk)
            rc.experiment_configuration = ec
        elif request_type == "update":
            rc = RoundConfiguration.objects.get(pk=pk)
        if form.cleaned_data.get('sequence_number') != rc.sequence_number:
            sort_round_configurations(rc.sequence_number, form.cleaned_data.get('sequence_number'),
                                      rc.experiment_configuration.pk)
        rc.round_type = form.cleaned_data.get('round_type')
        rc.sequence_number = form.cleaned_data.get('sequence_number')
        rc.display_number = form.cleaned_data.get('display_number')
        rc.duration = form.cleaned_data.get('duration')
        rc.template_id = form.cleaned_data.get('template_id')
        rc.survey_url = form.cleaned_data.get('survey_url')
        rc.session_id = form.cleaned_data.get('session_id')
        rc.repeat = form.cleaned_data.get('repeat')
        rc.randomize_groups = form.cleaned_data.get('randomize_groups')
        rc.preserve_existing_groups = form.cleaned_data.get('preserve_existing_groups')
        rc.create_group_clusters = form.cleaned_data.get('create_group_clusters')
        rc.initialize_data_values = form.cleaned_data.get('initialize_data_values')
        rc.chat_enabled = form.cleaned_data.get('chat_enabled')
        rc.save()

        return JsonResponse(dumps({
            'success': True,
            'round_config': rc.to_dict()
        }))
    #
    # logger.debug(form.errors)
    # logger.debug(form.non_field_errors())
    # message = '''<div class="alert alert-danger alert-dismissable alert-link"><button class=close data-dismiss=alert aria-hidden=true>&times;</button>{errors}</div>\n'''.format(
    #     errors='\n'.join(['<p>{e}</p>'.format(e=e) for e in form.non_field_errors()]))
    return JsonResponse(dumps({
        'success': False,
        'message': form.errors
    }))


@experimenter_required
def update_experiment_configuration(request, pk):
    form = ExperimentConfigurationForm(request.POST or None)

    if form.is_valid():
        try:
            ec = ExperimentConfiguration.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse(dumps({
                'success': False,
                'message': "Experiment Configuration with provided pk does not exist"
            }))

        ec.experiment_metadata = form.cleaned_data.get('experiment_metadata')
        ec.name = form.cleaned_data.get('name')
        ec.treatment_id = form.cleaned_data.get('treatment_id')
        ec.registration_email_subject = form.cleaned_data.get('registration_email_subject')
        ec.max_number_of_participants = form.cleaned_data.get('max_number_of_participants')
        ec.max_group_size = form.cleaned_data.get('max_group_size')
        ec.exchange_rate = form.cleaned_data.get('exchange_rate')
        ec.is_public = form.cleaned_data.get('is_public')
        ec.is_experimenter_driven = form.cleaned_data.get('is_experimenter_driven')
        ec.has_daily_rounds = form.cleaned_data.get('has_daily_rounds')

        ec.save()
        return JsonResponse(dumps({
            'success': True,
        }))

    return JsonResponse(dumps({
        'success': False,
        'message': form.errors
    }))


@experimenter_required
def edit_experiment_configuration(request, pk):
    ec = ExperimentConfiguration.objects.get(pk=pk)
    ecf = ExperimentConfigurationForm(instance=ec)

    epv = ExperimentParameterValue.objects.filter(experiment_configuration=ec)
    exp_param_values_list = [param.to_dict() for param in epv]

    exp_parameter_list = Parameter.objects.filter(scope='experiment').values('pk', 'name', 'type')
    #logger.debug(exp_param_values_list)

    round_config = RoundConfiguration.objects.filter(experiment_configuration=ec)
    round_config_list = [round.to_dict() for round in round_config]

    round_param_values = RoundParameterValue.objects.filter(round_configuration__in=round_config)
    round_param_values_list = [round_param.to_dict() for round_param in round_param_values]

    round_parameter_list = Parameter.objects.filter(scope='round').values('pk', 'name', 'type')

    # Get the round parameter values for each round
    for round in round_config_list:
        round["children"] = []
        for param in round_param_values_list:
            if round['pk'] == param['round_configuration_pk']:
                round["children"].append(param)  # set the round params list as this round's children

    json_data = {
        'expParamValuesList': exp_param_values_list,
        'expParameterList': [parameter for parameter in exp_parameter_list],
        'roundConfigList': round_config_list,
        'roundParameterList': [parameter for parameter in round_parameter_list]
    }

    return render(request, 'experimenter/edit-configuration.html', {
        'json_data': dumps(json_data),
        'experiment_config_form': ecf,
        'experiment_config': ec
    })


class OstromlabFaqList(ListView):
    model = OstromlabFaqEntry
    context_object_name = 'faq_entries'
    template_name = 'ostromlab/faq.html'


@experimenter_required
def clone_experiment_configuration(request):
    experiment_configuration_id = request.POST.get('experiment_configuration_id')
    logger.debug("cloning experiment configuration %s", experiment_configuration_id)
    experiment_configuration = get_object_or_404(ExperimentConfiguration, pk=experiment_configuration_id)
    experimenter = request.user.experimenter
    cloned_experiment_configuration = experiment_configuration.clone(creator=experimenter)
    return JsonResponse(dumps({'success': True, 'experiment_configuration': cloned_experiment_configuration.to_dict()}))


@login_required
def unsubscribe(request):
    user = request.user
    if is_participant(user) and user.participant.can_receive_invitations:
        successfully_unsubscribed = False
        if request.method == "POST":
            user = request.user
            user.participant.can_receive_invitations = False
            user.participant.save(update_fields=['can_receive_invitations'])
            successfully_unsubscribed = True
        return render(request, 'account/unsubscribe.html', {'successfully_unsubscribed': successfully_unsubscribed})
    else:
        return render(request, 'invalid_request.html',
                      {'message': "You aren't currently subscribed to our experiment session mailing list."})


"""
SUBJECT POOL VIEWS
"""


@experimenter_required
def subject_pool_index(request):
    """
    Returns by rendering the Subject Recruitment page with all the active experiment sessions and past experiment
    sessions.
    """
    experimenter = request.user.experimenter
    data = ExperimentSession.objects.filter(creator=request.user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]

    session_list = [session.to_dict() for session in data]

    session_data = {
        "session_list": session_list,
        "experiment_metadata_list": experiment_metadata_list
    }

    form = SessionInviteForm()

    return render(request, "experimenter/subject-pool-index.html",
                  {"view_model_json": dumps(session_data), "form": form})


@experimenter_required
@transaction.atomic
def update_session(request):
    """
    Depending upon the type of request, this view method can be used to create, update or delete Experiment sessions.
    """
    user = request.user
    form = SessionForm(request.POST or None)
    if form.is_valid():
        # if the form is valid get the experiment_session pk
        pk = form.cleaned_data.get('pk')
        request_type = form.cleaned_data.get('request_type')

        if request_type == 'delete':
            es = ExperimentSession.objects.get(pk=pk)
            es.delete()
        else:
            if request_type == 'create':
                es = ExperimentSession()
            elif request_type == 'update':
                es = ExperimentSession.objects.get(pk=pk)

            start_date = datetime.strptime(form.cleaned_data.get('start_date'), "%Y-%m-%d")
            start_time = time(int(form.cleaned_data.get('start_hour')), int(form.cleaned_data.get('start_min')))
            es.scheduled_date = datetime.combine(start_date, start_time)
            end_date = datetime.strptime(form.cleaned_data.get('end_date'), "%Y-%m-%d")
            end_time = time(int(form.cleaned_data.get('end_hour')), int(form.cleaned_data.get('end_min')))
            es.scheduled_end_date = datetime.combine(end_date, end_time)
            es.capacity = form.cleaned_data.get('capacity')
            es.location = form.cleaned_data.get('location')
            es.creator = user
            es.date_created = datetime.now()
            exp_pk = form.cleaned_data.get("experiment_metadata_pk")
            es.experiment_metadata = ExperimentMetadata.objects.get(pk=exp_pk)
            es.save()

        return JsonResponse(dumps({
            'success': True,
            'session': es
        }))

    error_list = [e for e in form.non_field_errors()]

    return JsonResponse(dumps({
        'success': False,
        'errors': error_list
    }))


@experimenter_required
def get_session_events(request):
    """
    Returns the list of Experiment sessions that fall within the given range,
    Used by the subject pool calendar to display experiment sessions falling within the date range shown
    """
    from_date = request.GET.get('from', None)
    to_date = request.GET.get('to', None)
    queryset = ExperimentSession.objects.select_related('experiment_metadata').filter()
    if to_date:
        queryset = queryset.filter(
            scheduled_end_date__gte=timestamp_to_datetime(from_date)
        )

    objects_body = []
    for event in queryset:
        index = event.pk % 20  # for color selection
        field = {
            "id": event.pk,
            "title": event.experiment_metadata.title,
            "url": "session/detail/event/" + str(event.pk),
            "class": "event-color-" + str(index),
            "start": datetime_to_timestamp(event.scheduled_date),
            "end": datetime_to_timestamp(event.scheduled_end_date),
            "capacity": event.capacity
        }
        objects_body.append(field)

    objects_head = {"success": True, "result": objects_body}

    return JsonResponse(dumps(objects_head))


def timestamp_to_datetime(timestamp):
    """
    Converts string timestamp to python datetime object with json fix
    """
    if isinstance(timestamp, (str, unicode)):

        if len(timestamp) == 13:
            timestamp = int(timestamp) / 1000

        return datetime.fromtimestamp(timestamp)
    else:
        return ""


def datetime_to_timestamp(date):
    """
    Converts python datetime object to timestamp with json fix
    """
    if isinstance(date, datetime):

        timestamp = mktime(date.timetuple())
        json_timestamp = int(timestamp) * 1000

        return '{0}'.format(json_timestamp)
    else:
        return ""


def get_invitations_count(request):
    """
    API endpoint that returns the potential participant count based on the selected experiment metadata and Institution
    """

    session_pk_list = request.POST.get('session_pk_list').split(",")
    affiliated_university = request.POST.get('affiliated_university')

    experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
    experiment_metadata_pk_list = experiment_sessions.values_list('experiment_metadata__pk', flat=True)

    if len(set(experiment_metadata_pk_list)) == 1:
        # As all sessions selected by experimenter to send invitations belong to same experiment metadata
        # get the experiment metadata pk of any session (This is ensured as it is a constraint)
        experiment_metadata_pk = experiment_metadata_pk_list[0]

        only_undergrad = request.POST.get('only_undergrad')

        potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_university,
                                                            only_undergrad=only_undergrad)
        return JsonResponse(dumps({
            'success': True,
            'invitesCount': len(potential_participants)
        }))
    else:
        return JsonResponse(dumps({
            'success': False,
            'invitesCount': 0
        }))


def get_invitation_email_content(custom_invitation_text, experiment_session_ids):
    plaintext_template = get_template('email/invitation-email.txt')
    c = Context({
        'invitation_text': custom_invitation_text,
        'session_list': ExperimentSession.objects.filter(pk__in=experiment_session_ids),
        'SITE_URL': settings.SITE_URL,
    })
    plaintext_content = plaintext_template.render(c)
    html_content = markdown.markdown(plaintext_content)

    return plaintext_content, html_content


@experimenter_required
def send_invitations(request):
    """
    Sends out invitation emails to random participants which match the required invitation criteria,
    using the provided email subject and message. Also returns the total number of invites sent.
    """
    user = request.user
    form = SessionInviteForm(request.POST or None)
    # Default Message
    message = "Please fill in all the details of the invitation form"

    if form.is_valid():
        invitation_subject = form.cleaned_data.get('invitation_subject')
        invitation_text = form.cleaned_data.get('invitation_text')
        # use currently logged in experimenter as the sender of the invitations.
        from_email = user.email

        session_pk_list = request.POST.get('session_pk_list').split(",")
        invitation_count = form.cleaned_data.get('number_of_people')
        affiliated_university = form.cleaned_data.get('affiliated_university')

        experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
        experiment_metadata_pk_list = experiment_sessions.values_list('experiment_metadata__pk', flat=True)

        if len(set(experiment_metadata_pk_list)) == 1:
            # get the experiment metadata pk of any session, as all sessions selected by experimenter to send invitations
            # belong to same experiment metadata (This is ensured as it is a constraint)
            experiment_metadata_pk = experiment_metadata_pk_list[0]

            potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_university,
                                                                only_undergrad=form.cleaned_data.get('only_undergrad'))
            potential_participants_count = len(potential_participants)

            final_participants = None

            if potential_participants_count == 0:
                final_participants = []
                message = "There are no more eligible participants that can be invited for this experiment."
            else:
                if potential_participants_count < invitation_count:
                    # less candidate participants than the number of requested participants, use them all
                    final_participants = potential_participants
                else:
                    final_participants = random.sample(potential_participants, invitation_count)
                message = "Your invitations were sent to %s / %s participants." % (
                    len(final_participants), invitation_count)

                today = datetime.now()
                invitations = []
                recipient_list = [settings.SERVER_EMAIL]
                for participant in final_participants:
                    recipient_list.append(participant.email)
                    for es in experiment_sessions:
                        invitations.append(
                            Invitation(participant=participant, experiment_session=es, date_created=today,
                                       sender=user))
                Invitation.objects.bulk_create(invitations)

                plaintext_content, html_content = get_invitation_email_content(invitation_text, session_pk_list)

                msg = EmailMultiAlternatives(subject=invitation_subject, body=plaintext_content, from_email=from_email,
                                             to=[from_email], bcc=recipient_list)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

            return JsonResponse(dumps({
                'success': True,
                'message': message,
                'invitesCount': len(final_participants)
            }))
        else:
            message = "To Invite Participants Please Select Experiment Sessions of same Experiment"
            return JsonResponse(dumps({
                'success': False,
                'message': message
            }))
    else:
        # Form is not valid
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def invite_email_preview(request):
    """
    Generates email Preview for the provided invitation details
    """
    form = SessionInviteForm(request.POST or None)
    message = "Please fill in all form fields to preview email"
    if form.is_valid():
        invitation_text = form.cleaned_data.get('invitation_text')
        session_pk_list = request.POST.get('session_pk_list').split(",")
        plaintext_content, html_content = get_invitation_email_content(invitation_text, session_pk_list)
        return JsonResponse(dumps({
            'success': True,
            'content': html_content
        }))
    else:
        # Form is not Valid
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def get_potential_participants(experiment_metadata_pk, institution="Arizona State University", days_threshold=7,
                               only_undergrad=True):
    """
    Returns the pool of participants which match the required invitation criteria.
    """

    try:
        affiliated_institution = Institution.objects.get(name=institution)
    except Institution.DoesNotExist:
        affiliated_institution = None
        return []

    # Get excluded participants for the given parameters
    excluded_participants = get_excluded_participants(days_threshold, experiment_metadata_pk)

    if only_undergrad:
        potential_participants = Participant.objects.filter(can_receive_invitations=True,
                                                            institution=affiliated_institution,
                                                            user__is_active=True,
                                                            class_status__in=Participant.UNDERGRADUATE_CLASS_CHOICES) \
            .exclude(pk__in=excluded_participants)
    else:
        potential_participants = Participant.objects.filter(can_receive_invitations=True,
                                                            institution=affiliated_institution,
                                                            user__is_active=True) \
            .exclude(pk__in=excluded_participants)
    return potential_participants


def get_excluded_participants(days_threshold, experiment_metadata_pk):
    """
    Returns the pool of participants which do not match the required invitation criteria.
    """
    last_week_date = datetime.now() - timedelta(days=days_threshold)
    # invited_in_last_threshold_days contains all Invitations that were generated in last threshold days for the
    # given Experiment metadata
    invited_in_last_threshold_days = Invitation.objects \
        .filter(date_created__gt=last_week_date, experiment_session__experiment_metadata__pk=experiment_metadata_pk) \
        .values_list('participant__pk', flat=True)

    # signup_participants is the list of participants who has already participated in the
    # given Experiment Metadata(in the past or currently participating)
    signup_participants = ParticipantSignup.objects.registered(experiment_metadata_pk=experiment_metadata_pk). \
        values_list('invitation__participant__pk', flat=True)

    # returned list the list of participants who have already received invitations in last threshold days or have already
    # participated in same experiment
    return list(set(invited_in_last_threshold_days) | set(signup_participants))


@experimenter_required
def manage_participant_attendance(request, pk=None):
    """
    Performs Update or Get operation on the ParticipantSignup model depending upon the request.
    If request is GET, then the function will return the attendance formset. If request is POST then
    the function will update the Participant Attendance and return the updated formset.
    """
    es = ExperimentSession.objects.get(pk=pk)

    if es.creator == request.user:
        invitations_sent = Invitation.objects.filter(experiment_session=es)
        session_detail = dict(pk=es.pk, experiment_metadata=es.experiment_metadata, start_date=es.scheduled_date.date(),
                              start_time=es.scheduled_date.strftime('%I:%M %p'), end_date=es.scheduled_end_date.date(),
                              end_time=es.scheduled_end_date.strftime('%I:%M %p'), location=es.location,
                              capacity=es.capacity)

        attendanceformset = modelformset_factory(ParticipantSignup, form=ParticipantAttendanceForm,
                                                 exclude=('date_created',), extra=0)

        if request.method == "POST":
            formset = attendanceformset(request.POST,
                                        queryset=ParticipantSignup.objects.select_related(
                                            'invitation__participant__user').
                                        filter(invitation__in=invitations_sent))
            if formset.is_valid():
                messages.add_message(request, messages.SUCCESS, 'Well done...Your changes were successfully saved.')
                if formset.has_changed():
                    formset.save()
            else:
                messages.add_message(request, messages.ERROR,
                                     'Something went wrong...Your changes were not saved. Please try again')
        else:
            formset = attendanceformset(
                queryset=ParticipantSignup.objects.select_related('invitation__participant__user').
                filter(invitation__in=invitations_sent))

        return render(request, 'experimenter/session_detail.html',
                      {'session_detail': session_detail, 'formset': formset})
    else:
        raise PermissionDenied("You don't have access to this experiment.")


@participant_required
def cancel_experiment_session_signup(request):
    form = CancelSignupForm(request.POST or None)
    if form.is_valid():
        signup = form.signup
        invitation = signup.invitation
        es = invitation.experiment_session
        if request.user.participant == invitation.participant:
            signup.delete()
            messages.add_message(request, messages.SUCCESS,
                                 _("You are no longer signed up for %s - thanks for letting us know!" % es))
        else:
            logger.error("Invalid request: Participant %s tried to cancel signup %s", request.user.participant, signup)
            messages.add_message(request, messages.ERROR, _("You don't appear to be signed up for this session."))
    else:
        messages.add_message(request, messages.ERROR, _("Sorry, we couldn't process your request"))
    return redirect('core:dashboard')


@participant_required
def submit_experiment_session_signup(request):
    """
    Enrolls the currently logged in user in the selected experiment session.
    """
    user = request.user
    invitation_pk = request.POST.get('invitation_pk')
    experiment_metadata_pk = request.POST.get('experiment_metadata_pk')
    invitation = Invitation.objects.select_related('experiment_session').get(pk=invitation_pk)

    # lock on the experiment session to prevent concurrent participant signups for an experiment session
    # exceeding its capacity
    with transaction.atomic():
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=invitation.experiment_session.pk).count()
        # verify for the vacancy in the selected experiment session before creating participant signup entry
        if signup_count < invitation.experiment_session.capacity:
            try:
                ps = ParticipantSignup.objects.get(
                    invitation__participant=user.participant,
                    invitation__experiment_session__experiment_metadata__pk=experiment_metadata_pk,
                    attendance=ParticipantSignup.ATTENDANCE.registered)
            except ParticipantSignup.DoesNotExist:
                ps = ParticipantSignup()

            ps.invitation = invitation
            ps.date_created = datetime.now()
            ps.attendance = ParticipantSignup.ATTENDANCE.registered
            ps.save()
            success = True
        else:
            # No vacancy
            success = False

    if success:
        messages.success(request, _(
            "You are now registered for this experiment session. A confirmation email has been sent and you should also receive a reminder email one day before the session. Thanks in advance for participating!"))
        chosen_session = ExperimentSession.objects.get(pk=invitation.experiment_session.pk)
        send_email("subject-pool/email/confirmation-email.txt", {'session': chosen_session}, "Confirmation Email",
                   settings.SERVER_EMAIL, [user.email])
        return redirect('core:dashboard')
    else:
        messages.error(request, _("This session is currently full."))
        return redirect('core:experiment_session_signup')


@experimenter_required
def download_experiment_session(request, pk=None):
    user = request.user
    experiment_session = get_object_or_404(ExperimentSession.objects.select_related('creator'), pk=pk)

    if experiment_session.creator != user:
        logger.error("unauthorized access to %s from %s", experiment_session, user)
        raise PermissionDenied("You don't have access to this experiment.")

    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename=participants.csv'
    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(["Participant list", experiment_session, experiment_session.location, experiment_session.capacity,
                     experiment_session.creator])
    writer.writerow(['Email', 'Name', 'Username', 'Class Status', 'Attendance'])
    for ps in ParticipantSignup.objects.select_related('invitation__participant').filter(
            invitation__experiment_session=experiment_session):
        participant = ps.invitation.participant
        writer.writerow(
            [participant.email, participant.full_name, participant.username, participant.class_status, ps.attendance])
    return response


@participant_required
def experiment_session_signup(request):
    """
    Returns and renders all the experiment session invitation that currently logged in participant has received
    """
    user = request.user
    session_unavailable = False

    # If the Experiment Session is being conducted tomorrow then don't show invitation to user
    tomorrow = datetime.now() + timedelta(days=1)

    active_experiment_sessions = ParticipantSignup.objects \
        .select_related('invitation', 'invitation__experiment_session') \
        .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.registered,
                invitation__experiment_session__scheduled_date__gt=tomorrow)

    # Making sure that user don't see invitations for a experiment for which he has already participated
    # useful in cases when the experiment has lots of sessions spanning to lots of days. It avoids a user to participate
    # in another experiment session after attending one of the experiment session of same experiment in last couple
    # of days
    participated_experiment_metadata = ParticipantSignup.objects \
        .select_related('invitation', 'invitation__experiment_session',
                        'invitation__experiment_session__experiment_metadata') \
        .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.participated)

    participated_experiment_metadata_pk_list = [ps.invitation.experiment_session.experiment_metadata.pk for ps in
                                                participated_experiment_metadata]

    active_invitation_pk_list = [ps.invitation.pk for ps in active_experiment_sessions]

    invitations = Invitation.objects.select_related('experiment_session', 'experiment_session__experiment_metadata__pk') \
        .filter(participant=user.participant, experiment_session__scheduled_date__gt=tomorrow) \
        .exclude(experiment_session__experiment_metadata__pk__in=participated_experiment_metadata_pk_list) \
        .exclude(pk__in=active_invitation_pk_list)

    invitation_list = []
    for ps in active_experiment_sessions:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=ps.invitation.experiment_session.pk).count()
        ps_dict = ps.to_dict(signup_count)
        invitation_list.append(ps_dict)

    for invite in invitations:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=invite.experiment_session.pk).count()
        invite_dict = invite.to_dict(signup_count)

        if invite_dict['invitation']['openings'] != 0 and session_unavailable:
            session_unavailable = False
        invitation_list.append(invite_dict)

    invitation_list = sorted(invitation_list, key=lambda use_key: use_key['invitation']['scheduled_date'])

    if session_unavailable:
        messages.error(request, _(
            "All experiment sessions are full. Signups are first-come, first-serve. Please try again later, you are still eligible to participate in future experiments and may receive future invitations for this experiment."))

    return render(request, "participant/experiment-session-signup.html", {"invitation_list": invitation_list})
