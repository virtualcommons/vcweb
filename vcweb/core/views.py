from collections import defaultdict
import socket
import urllib2
import xml.etree.ElementTree as ET
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
# from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.forms import PasswordResetForm
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from vcweb import settings
from vcweb.core import dumps
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
from vcweb.core.forms import (RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm,
                              ParticipantGroupIdForm, RegisterEmailListParticipantsForm, RegisterTestParticipantsForm,
                              RegisterExcelParticipantsForm, LogMessageForm, BookmarkExperimentMetadataForm)
from vcweb.core.http import JsonResponse
from vcweb.core.models import (User, ChatMessage, Participant, ParticipantExperimentRelationship,
                               ParticipantGroupRelationship, ExperimentConfiguration, ExperimenterRequest, Experiment, ExperimentMetadata,
                               Institution, is_participant, is_experimenter, BookmarkedExperimentMetadata, Invitation, ParticipantSignup,
                               ExperimentSession, Experimenter)
import unicodecsv
from vcweb.core.validate_jsonp import is_valid_jsonp_callback_value
import itertools
import tempfile
from datetime import datetime, timedelta

import mimetypes

mimetypes.init()

import logging

logger = logging.getLogger(__name__)

SUCCESS_JSON = dumps({'success': True})
FAILURE_JSON = dumps({'success': False})


def json_response(request, content, **http_response_kwargs):
    "Construct an `HttpResponse` object."
    callback = request.GET.get('callback', '')
    content_type = 'application/json'
    if is_valid_jsonp_callback_value(callback):
        content = '%s(%s)' % (callback, content)
        content_type = 'application/javascript'
    return HttpResponse(content, content_type=content_type, **http_response_kwargs)


class JSONResponseMixin(object):
    def render_to_response(self, context, **kwargs):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context, **kwargs))

    def get_json_response(self, content, **httpresponse_kwargs):
        return json_response(self.request, content, **httpresponse_kwargs)

    def convert_context_to_json(self, context, context_key='object_list', **kwargs):
        """
        Converts the data object associated with context_key in the context dict
        into a JSON object and returns it.  If context_key is None, converts the
        entire context dict.
        """
        return dumps(context if context_key is None else context[context_key])


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
    def __init__(self, user=None):
        self.is_experimenter = is_experimenter(user)
        if self.is_experimenter:
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
        else:
            self.participant = user.participant
            experiment_status_dict = defaultdict(list)
            for e in self.participant.experiments.select_related('experiment_configuration').all():
                experiment_status_dict[e.status].append(
                    e.to_dict(attrs=('participant_url', 'start_date'), name=e.experiment_metadata.title))
            self.pending_experiments = experiment_status_dict['INACTIVE']
            self.running_experiments = experiment_status_dict['ACTIVE'] + experiment_status_dict['ROUND_IN_PROGRESS']

    @property
    def template_name(self):
        if self.is_experimenter:
            return 'experimenter/dashboard.html'
        else:
            return 'participant/dashboard.html'

    def to_json(self):
        return dumps(self.to_dict())

    def to_dict(self):
        if self.is_experimenter:
            return {
                'experimentMetadataList': self.experiment_metadata_list,
                'pendingExperiments': self.pending_experiments,
                'runningExperiments': self.running_experiments,
                'archivedExperiments': self.archived_experiments
            }
        else:
            return {
                'pendingExperiments': self.pending_experiments,
                'runningExperiments': self.running_experiments
            }


@login_required
def dashboard(request):
    """
    selects the appropriate dashboard template and data for participants and experimenters
    """
    user = request.user
    if is_participant(user):
        # first_login = (user.last_login - user.date_joined) <= timedelta(seconds=5)
        profile_complete = is_profile_complete(user.participant)
        if not profile_complete:
            return redirect('core:profile')

    dashboard_view_model = DashboardViewModel(user)
    return render(request, dashboard_view_model.template_name,
                  {'dashboardViewModelJson': dashboard_view_model.to_json()})


def is_profile_complete(participant):
    if participant.can_receive_invitations:
        if participant.class_status and participant.gender and participant.favorite_sport and participant.favorite_color and participant.favorite_food and participant.favorite_movie_genre:
            return True
        else:
            return False
    else:
        return False


@login_required
def get_dashboard_view_model(request):
    return JsonResponse(dumps({'success': True, 'dashboardViewModelJson': DashboardViewModel(request.user).to_json()}))


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
            email = form.cleaned_data.get('email')
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
            email = form.cleaned_data.get('email')
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

            for attr in ('major', 'class_status', 'gender', 'can_receive_invitations', 'favorite_food', 'favorite_sport',
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
    email = request.GET.get("email")
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

    def check_user(self, user, experiment):
        return experiment

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk', None)
        experiment = get_object_or_404(
            Experiment.objects.select_related('experiment_metadata', 'experiment_configuration', 'experimenter'), pk=pk)
        return self.check_user(experiment)


class ParticipantSingleExperimentMixin(SingleExperimentMixin, ParticipantMixin):
    def check_user(self, experiment):
        user = self.request.user
        if experiment.participant_set.filter(participant__user=user).count() == 1:
            return experiment
        logger.warning("unauthz access to experiment %s by user %s", experiment, user)
        raise PermissionDenied("You do not have access to %s" % experiment)


class ExperimenterSingleExperimentMixin(SingleExperimentMixin, ExperimenterMixin):
    def check_user(self, experiment):
        user = self.request.user
        if is_experimenter(user, experiment.experimenter):
            return experiment
        logger.warning("unauthz access to experiment %s by user %s", experiment, user)
        raise PermissionDenied("You do not have access to %s" % experiment)


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


def upload_excel_participants_file(request):
    if request.method == 'POST':
        form = RegisterExcelParticipantsForm(request.POST, request.FILES)
        if form.is_valid():
            import xlrd

            participant = request.user.participant
            experiment_id = form.cleaned_data.get('experiment_pk')
            experiment = get_object_or_404(Experiment, pk=experiment_id)
            uploaded_file = request.FILES['file']
            with tempfile.NamedTemporaryFile() as dst:
                for chunk in uploaded_file.chunks():
                    dst.write(chunk)
                workbook = xlrd.open_workbook(filename=dst.name)
                logger.debug("workbook: %s", workbook)


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

# FIXME: these last two use GET (which should be idempotent) to modify database state which makes HTTP sadful
class CloneExperimentView(ExperimenterSingleExperimentView):
    def process(self):
        self.experiment = self.experiment.clone()
        return self.experiment

    def render_to_response(self, context):
        return redirect('core:monitor_experiment', pk=self.experiment.pk)


class ClearParticipantsExperimentView(ExperimenterSingleExperimentView):
    def process(self):
        e = self.experiment
        logger.debug("clearing all participants for experiment %s", e)
        ParticipantExperimentRelationship.objects.filter(experiment=e).delete()
        e.deactivate()
        ParticipantGroupRelationship.objects.filter(group__experiment=e).delete()
        return e

    def render_to_response(self, context):
        return redirect('core:dashboard')


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
    for round_data in experiment.round_data_set.select_related('round_configuration').all():
        round_number = round_data.round_number
        # emit all participant data values
        for data_value in round_data.participant_data_value_set.select_related(
                'participant_group_relationship__group').all():
            pgr = data_value.participant_group_relationship
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
def experiment_controller(request, pk=None, experiment_action=None):
    try:
        experimenter = request.user.experimenter
        experiment = Experiment.objects.get(pk=pk)
        # TODO: provide experimenter access to other users besides the creator of the
        # experiment?
        if experimenter == experiment.experimenter:
            # FIXME: dangerous to expose all experiment methods, even if it's only to the experimenter, should expose
            # via experiment.invoke(action, experimenter) instead
            experiment_func = getattr(experiment, experiment_action.replace('-', '_'), None)
            if hasattr(experiment_func, '__call__'):
                # pass params?  start_round() takes a sender for instance..
                experiment_func()
                return redirect('core:monitor_experiment', pk=pk)
            else:
                error_message = "Invalid experiment action: You ({experimenter}) tried to invoke {experiment_action} on {experiment}".format(
                    experimenter=experimenter, experiment_action=experiment_action, experiment=experiment)
        else:
            error_message = "Access denied for {experimenter}: You do not have permission to invoke {experiment_action} on {experiment}".format(
                experimenter=experimenter, experiment_action=experiment_action, experiment=experiment)

    except Experiment.DoesNotExist:
        error_message = 'Could not invoke {experiment_action} on a non-existent experiment (id: {pk}, experimenter: {experimenter})'.format(
            experimenter=experimenter, experiment_action=experiment_action, pk=pk)

    logger.warning(error_message)
    messages.warning(request, error_message)
    return redirect('core:dashboard')


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
    return json_response(request, dumps({'success': success}))


@participant_required
def completed_survey(request):
    pgr_id = request.GET.get('pid', None)
    success = False
    try:
        if pgr_id is None:
            participant = request.user.participant
            experiment = get_active_experiment(participant)
            pgr = experiment.get_participant_group_relationship(participant)
        else:
            pgr = get_object_or_404(ParticipantGroupRelationship, pk=pgr_id)
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


# FIXME: replace magic numbers with constant references
@participant_required
def get_participant_sessions(request):
    user = request.user
    success = None
    if request.method == 'POST':
        data = dict(request.POST.iteritems())
        invitation_pk = None
        experiment_metadata_pk = None

        for key in data:
            if key != 'experiment_metadata_pk':
                invitation_pk = int(data[key])
            else:
                experiment_metadata_pk = int(data[key])

        if invitation_pk is not None:
            inv = Invitation.objects.get(pk=invitation_pk)
            # lock on the experiment session to prevent concurrent participant signups for an experiment session
            # exceeding its capacity
            lock = ExperimentSession.objects.select_for_update().get(pk=inv.experiment_session.pk)
            signup_count = ParticipantSignup.objects.filter(
                invitation__experiment_session__pk=inv.experiment_session.pk).count()

            ps = ParticipantSignup.objects.filter(
                invitation__participant=user.participant,
                invitation__experiment_session__experiment_metadata__pk=experiment_metadata_pk,
                attendance=ParticipantSignup.ATTENDANCE.registered)

            if signup_count < inv.experiment_session.capacity:
                if not ps:
                    ps = ParticipantSignup()
                else:
                    ps = ps[0]

                ps.invitation = inv
                ps.date_created = datetime.now()
                ps.attendance = ParticipantSignup.ATTENDANCE.registered
                ps.save()
                success = True
            else:
                if ps:
                    success = (ps[0].invitation.pk == invitation_pk)
                else:
                    success = False
            lock.save()
        else:
            ParticipantSignup.objects \
                .select_related('invitation', 'invitation__experiment_session__experiment_metadata') \
                .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.registered,
                        invitation__experiment_session__experiment_metadata__pk=experiment_metadata_pk).delete()
            success = True

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
    # logger.debug(participated_experiment_metadata_pk_list)
    active_invitation_pk_list = [ps.invitation.pk for ps in active_experiment_sessions]
    # logger.debug(active_invitation_pk_list)
    invitations = Invitation.objects.select_related('experiment_session', 'experiment_session__experiment_metadata__pk') \
        .filter(participant=user.participant, experiment_session__scheduled_date__gt=tomorrow) \
        .exclude(experiment_session__experiment_metadata__pk__in=participated_experiment_metadata_pk_list) \
        .exclude(pk__in=active_invitation_pk_list)

    # logger.debug(invitations)
    invitation_list = []
    for ps in active_experiment_sessions:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=ps.invitation.experiment_session.pk).count()

        invitation_list.append(ps.to_dict(signup_count))

    for invite in invitations:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=invite.experiment_session.pk).count()

        invitation_list.append(invite.to_dict(signup_count))

    new_list = sorted(invitation_list, key=lambda key: key['invitation']['scheduled_date'])
    return render(request, "participant/participant-index.html", {"invitation_list": new_list, "success": success})


def get_cas_user(tree):
    username = tree[0][0].text
    user, user_created = User.objects.get_or_create(username=username)

    if user_created:
        url = settings.WEB_DIRECTORY_URL + username

        r = urllib2.Request(url, headers={"Accept": "application/xml"})
        parsed = ET.parse(urllib2.urlopen(r))
        root = parsed.getroot()

        person = root.find('person')
        first_name = person.find('firstName').text
        last_name = person.find('lastName').text
        email = person.find('email').text

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        password = User.objects.make_random_password()
        user.set_password(password)
        user.save()

        plans = person.find('plans')
        plan = plans.find('plan')
        major = plan.find('acadPlanDescr').text
        institution, institution_created = Institution.objects.get_or_create(name=settings.CAS_UNIVERSITY_NAME)
        if institution_created:
            institution.url = settings.CAS_UNIVERSITY_URL
            institution.cas_server_url = settings.CAS_SERVER_URL
            institution.save()

        reset_password(email)
        participant = Participant(user=user)
        participant.major = major
        participant.institution = institution
        participant.institution_username = username
        participant.save()


def reset_password(email, from_email='vcweb@asu.edu', template='registration/password_reset_email.html'):
    form = PasswordResetForm({'email': email})
    if form.is_valid():
        # domain = socket.gethostbyname(socket.gethostname())
        domain = "vcweb.asu.edu"
        return form.save(from_email=from_email, email_template_name=template, domain_override=domain)
    return None


def handler500(request):
    return render(request, '500.html')


def edit_experiment_configuration(request, pk):
    pass

@experimenter_required
def clone_experiment_configuration(request):
    experiment_configuration_id = request.POST.get('experiment_configuration_id')
    logger.debug("cloning experiment configuration %s", experiment_configuration_id)
    experiment_configuration = get_object_or_404(ExperimentConfiguration, pk=experiment_configuration_id)
    experimenter = request.user.experimenter
    cloned_experiment_configuration = experiment_configuration.clone(creator=experimenter)
    return JsonResponse(dumps({'success': True, 'experiment_configuration': cloned_experiment_configuration.to_dict()}))
