from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.utils.decorators import method_decorator
from django.views.generic import ListView, FormView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.views.generic.edit import UpdateView
from vcweb.core import dumps
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
from vcweb.core.forms import (RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm,
        RegisterEmailListParticipantsForm, RegisterSimpleParticipantsForm, RegisterExcelParticipantsForm, LogMessageForm)
from vcweb.core.models import (User, ChatMessage, Participant, ParticipantExperimentRelationship, ParticipantGroupRelationship,
        ExperimenterRequest, Experiment, ExperimentMetadata, Institution, is_participant, is_experimenter)
from vcweb.core.unicodecsv import UnicodeWriter
from vcweb.core.validate_jsonp import is_valid_jsonp_callback_value
import itertools
import logging
import mimetypes
import tempfile
logger = logging.getLogger(__name__)


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
        return dumps( context if context_key is None else context[context_key] )

class AnonymousMixin(object):
    """ provides the anonymous_required decorator """
    @method_decorator(anonymous_required)
    def dispatch(self, *args, **kwargs):
        return super(AnonymousMixin, self).dispatch(*args, **kwargs)

class Dashboard(ListView, TemplateResponseMixin):
    """
    general dashboard for participants or experimenters that displays a list of
    experiments to either participate in or configure/manage/monitor, respectively
    """
    context_object_name = 'experiments'
    def get_template_names(self):
        user = self.request.user
# FIXME: need to replace participant dashboard with a landing page that displays only the active experiment they can
# participate in.
        if is_experimenter(user):
            return [ 'experimenter/dashboard.html' ]
        else:
            return [ 'participant/dashboard.html' ]

    def get_queryset(self):
        user = self.request.user
        if is_experimenter(user):
            return Experiment.objects.filter(experimenter__pk=self.request.user.experimenter.pk)
        else:
# nested dictionary, {ExperimentMetadata -> { status -> [experiments,...] }}
# FIXME: could also use collections.defaultdict or regroup template tag to
# accomplish this..
            experiment_dict = {}
            for experiment in user.participant.experiments.exclude(status__in=(Experiment.INACTIVE, Experiment.PAUSED, Experiment.COMPLETED)):
                if not experiment.experiment_metadata in experiment_dict:
                    experiment_dict[experiment.experiment_metadata] = dict([(choice[0], list()) for choice in Experiment.STATUS])
                experiment_dict[experiment.experiment_metadata][experiment.status].append(experiment)
                logger.info("experiment_dict %s", experiment_dict)
            return experiment_dict

def set_authentication_token(user, authentication_token=None):
    commons_user = None
    if is_participant(user):
        commons_user = user.participant
    elif is_experimenter(user):
        commons_user = user.experimenter
    else:
        logger.error("Invalid user: %s", user)
        raise Http404
    logger.debug("%s authentication_token=%s", commons_user, authentication_token)
    commons_user.authentication_token = authentication_token
    commons_user.save()

def get_active_experiment(participant, experiment_metadata=None, **kwargs):
    pers = []
    if experiment_metadata is not None:
        pers = ParticipantExperimentRelationship.objects.active(participant=participant, experiment__experiment_metadata=experiment_metadata, **kwargs)
    else:
        pers = ParticipantExperimentRelationship.objects.active(participant=participant, **kwargs)
    if pers:
        logger.debug("using first active experiment %s for participant %s", pers[0], participant)
        return pers[0].experiment
    return None


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
        for experiment in Experiment.objects.public():
            experiment.add_participant(participant)
        return super(RegistrationView, self).form_valid(form)

    def get_success_url(self):
        return reverse('core:dashboard')

class AccountView(FormView):
    pass


@login_required
def account_profile(request):
    user = request.user
    if is_participant(user):
        form = ParticipantAccountForm()
    else:
        form = ExperimenterAccountForm(instance=user.experimenter)
    return render_to_response('account/profile.html', { 'form': form }, context_instance=RequestContext(request))

''' participant views '''
class ParticipantMixin(object):
    @method_decorator(participant_required)
    def dispatch(self, *args, **kwargs):
        return super(ParticipantMixin, self).dispatch(*args, **kwargs)

@login_required
def instructions(request, namespace=None):
    if namespace is not None:
        return render_to_response('%s/instructions.html' % namespace,
                context_instance=RequestContext(request))
    else:
        return redirect('home')

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
        return { "experiment_pk" : self.object.pk }

    def process(self):
        pass
    def check_user(self, user, experiment):
        return experiment

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk', None)
        experiment = get_object_or_404(Experiment, pk=pk)
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

class MonitorExperimentView(ExperimenterSingleExperimentMixin, DetailView):
    template_name = 'experimenter/monitor.html'

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

class RegisterEmailListView(ExperimenterSingleExperimentMixin, FormView):
    form_class = RegisterEmailListParticipantsForm
    template_name = 'experimenter/register-email-participants.html'
    def form_valid(self, form):
        emails = form.cleaned_data.get('participant_emails')
        institution = form.cleaned_data.get('institution')
        experiment = self.object
        logger.debug("registering participants %s for experiment: %s", emails, experiment)
        experiment.authentication_code = form.cleaned_data.get('experiment_passcode')
        experiment.save()
        experiment.register_participants(emails=emails, institution=institution,
                password=experiment.authentication_code)
        return super(RegisterEmailListView, self).form_valid(form)
    def get_success_url(self):
        return reverse('core:dashboard')

class RegisterSimpleParticipantsView(ExperimenterSingleExperimentMixin, FormView):
    form_class = RegisterSimpleParticipantsForm
    template_name = 'experimenter/register-simple-participants.html'

    def form_valid(self, form):
        number_of_participants = form.cleaned_data.get('number_of_participants')
        email_suffix = form.cleaned_data.get('email_suffix')
        experiment = self.object
        experiment_passcode = form.cleaned_data.get('experiment_passcode')
        experiment.setup_test_participants(count=number_of_participants,
                institution=form.institution,
                email_suffix=email_suffix,
                password=experiment_passcode)
        return super(RegisterSimpleParticipantsView, self).form_valid(form)

    def get_success_url(self):
        return reverse('core:dashboard')

# FIXME: these last two use GET (which should be idempotent) to modify database state which makes HTTP sadful
class CloneExperimentView(ExperimenterSingleExperimentView):
    def process(self):
        return self.experiment.clone()
    def render_to_response(self, context):
        return redirect('core:dashboard')

class ClearParticipantsExperimentView(ExperimenterSingleExperimentView):
    def process(self):
        self.experiment.participant_set.all().delete()
        return self.experiment
    def render_to_response(self, context):
        return redirect('core:dashboard')

# FIXME: replace method with class-based view later (if beneficial)
class AddExperimentView(ExperimenterMixin, TemplateView):
    pass

@experimenter_required
def add_experiment(request):
    return render_to_response('experimenter/add-experiment.html',
            { 'experiment_list': ExperimentMetadata.objects.all() },
            context_instance=RequestContext(request))

mime_types = mimetypes.MimeTypes(filenames=('/etc/mime.types',))

class DataExportMixin(ExperimenterSingleExperimentMixin):
    file_extension = '.csv'
    def render_to_response(self, context, **response_kwargs):
        experiment = self.get_object()
        file_ext = self.file_extension
        if file_ext in mime_types.types_map:
            content_type = mime_types.types_map[file_ext]
        else:
            content_type = 'application/octet-stream'
        response = HttpResponse(content_type=content_type)
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name(file_ext=file_ext)
        self.export_data(response, experiment)
        return response

class CsvDataExporter(DataExportMixin):
    def export_data(self, response, experiment):
        writer = UnicodeWriter(response)
        writer.writerow(['Group', 'Members'])
        for group in experiment.group_set.all():
            writer.writerow(itertools.chain.from_iterable([[group], group.participant_set.all()]))
        for round_data in experiment.round_data_set.all():
            round_configuration = round_data.round_configuration
        # write out group-wide and participant data values
            writer.writerow(['Owner', 'Round', 'Data Parameter', 'Data Parameter Value', 'Created On', 'Last Modified'])
            for data_value in itertools.chain(round_data.group_data_value_set.all(), round_data.participant_data_value_set.all()):
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
    content_type = mime_types.types_map[file_extension]
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
    response = HttpResponse(content_type=mime_types.types_map['.%s' % file_type])
    response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name()
    writer = UnicodeWriter(response)
    writer.writerow(['Group', 'Members'])
    for group in experiment.group_set.all():
        writer.writerow(itertools.chain.from_iterable([[group], group.participant_set.all()]))
    for round_data in experiment.round_data_set.all():
        round_configuration = round_data.round_configuration
        # write out group-wide and participant data values
        writer.writerow(['Owner', 'Round', 'Data Parameter', 'Data Parameter Value', 'Created On', 'Last Modified'])
        for data_value in itertools.chain(round_data.group_data_value_set.all(), round_data.participant_data_value_set.all()):
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

# FIXME: unimplemented: add filters by round_data parameters
def daily_report(request, pk=None, parameter_ids=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    round_data = experiment.current_round_data
    pass

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


def handler500(request):
    return render_to_response('500.html', context_instance=RequestContext(request))

