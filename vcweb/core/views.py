from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.utils.decorators import method_decorator
from django.views.generic import ListView, FormView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.detail import SingleObjectMixin, DetailView
from django.views.generic.edit import UpdateView
from vcweb.core.forms import (RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm,
        RegisterEmailListParticipantsForm, RegisterSimpleParticipantsForm)
from vcweb.core.models import (Participant, Experimenter, Experiment, Institution, is_participant, is_experimenter)
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
from vcweb.core import unicodecsv
import itertools
import logging
logger = logging.getLogger(__name__)

""" account registration / login / logout / profile views """

class AnonymousMixin(object):
    @method_decorator(anonymous_required)
    def dispatch(self, *args, **kwargs):
        return super(AnonymousMixin, self).dispatch(*args, **kwargs)

class Dashboard(ListView, TemplateResponseMixin):
    context_object_name = 'experiments'
    def get_template_names(self):
        user = self.request.user
        return ['experimenter/dashboard.html'] if is_experimenter(user) else ['participant/dashboard.html']
    def get_queryset(self):
        user = self.request.user
        if is_experimenter(user):
            return Experiment.objects.filter(experimenter__pk=self.request.user.experimenter.pk)
        else:
# nested dictionary, {ExperimentMetadata -> { status -> [experiments,...] }}
            experiment_dict = {}
            for experiment in user.participant.experiments.exclude(status__in=(Experiment.INACTIVE, Experiment.PAUSED, Experiment.COMPLETED)):
                if not experiment.experiment_metadata in experiment_dict:
                    experiment_dict[experiment.experiment_metadata] = dict([(choice[0], list()) for choice in Experiment.STATUS_CHOICES])
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
        logger.error("Invalid user: %s" % user)
        return
    commons_user.authentication_token = authentication_token
    commons_user.save()

class LoginView(FormView, AnonymousMixin):
    form_class = LoginForm
    template_name = 'registration/login.html'
    def form_valid(self, form):
        request = self.request
        user = form.user_cache
        auth.login(request, user)
        logger.debug("session is %s" % request.session)
        set_authentication_token(user, request.session.session_key)
        return super(LoginView, self).form_valid(form)
    def get_success_url(self):
        return_url = self.request.GET.get('next')
        return return_url if return_url else reverse('core:dashboard')

class LogoutView(TemplateView):
    def get(self, request, *args, **kwargs):
        user = request.user
        set_authentication_token(user)
        auth.logout(request)
        return redirect('home')

class RegistrationView(FormView, AnonymousMixin):
    form_class = RegistrationForm
    template_name = 'registration/register.html'
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
            experimenter = Experimenter.objects.create(user=user,
                    institution=institution)
            logger.debug("creating new experimenter: %s, adding default forestry experiment" % experimenter)
	    # FIXME: hard coded slovakia experiment, get rid of this!
            experiment = Experiment.objects.get(pk=1)
            experiment.clone(experimenter=experimenter)
        else:
            participant = Participant.objects.create(user=user, institution=institution)
            logger.debug("Creating new participant: %s" % participant)
        request = self.request
        auth.login(request, auth.authenticate(username=email, password=password))
        set_authentication_token(user, request.session.session_key)
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
    return render_to_response('registration/profile.html', { 'form': form }, context_instance=RequestContext(request))

''' participant views '''
class ParticipantMixin(object):
    @method_decorator(participant_required)
    def dispatch(self, *args, **kwargs):
        return super(ParticipantMixin, self).dispatch(*args, **kwargs)

@login_required
def instructions(request, pk=None, namespace=None):
    if pk:
        experiment = Experiment.objects.get(pk=pk)
    elif namespace:
        experiment = Experiment.objects.get(experiment_metadata__namespace=namespace)

    if not experiment:
        logger.warning("Tried to request instructions for id %s or namespace %s" % (pk, namespace))
        return redirect('home')

    return render_to_response(experiment.get_template_path('instructions.html'), locals(), context_instance=RequestContext(request))

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

    def process_experiment(self, experiment):
        pass
    def check_user(self, user, experiment):
        return experiment

    def get_object(self, queryset=None):
        pk = self.kwargs.get('pk', None)
        experiment = Experiment.objects.get(pk=pk)
        user = self.request.user
        return self.check_user(user, experiment)

class ParticipantSingleExperimentMixin(SingleExperimentMixin, ParticipantMixin):
    def check_user(self, user, experiment):
        # FIXME: should we do a user.participant in experiment.participants.all() check?
        return experiment

class ExperimenterSingleExperimentMixin(SingleExperimentMixin, ExperimenterMixin):
    def check_user(self, user, experiment):
        if self.request.user.experimenter == experiment.experimenter:
            return experiment
        raise PermissionDenied("You do not have access to %s" % experiment)

class ExperimenterSingleExperimentView(ExperimenterSingleExperimentMixin, TemplateView):
    def get(self, request, **kwargs):
        self.object = self.get_object()
        self.process_experiment(self.object)
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

class MonitorExperimentView(ExperimenterSingleExperimentMixin, DetailView):
    template_name = 'experimenter/monitor.html'

class RegisterEmailListView(ExperimenterSingleExperimentMixin, UpdateView):
    form_class = RegisterEmailListParticipantsForm
    template_name = 'experimenter/register-email-participants.html'
    def form_valid(self, form):
        emails = form.cleaned_data.get('participant_emails')
        experiment = self.object
        logger.debug("registering participants %s for experiment: %s" % (emails, experiment))
        experiment.authentication_code = form.cleaned_data.get('experiment_passcode')
        experiment.register_participants(emails=emails, institution=form.institution,
                password=experiment.authentication_code)


class RegisterSimpleParticipantsView(ExperimenterSingleExperimentMixin, UpdateView):
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

# FIXME: uses GET (which should be idempotent) to modify database state which makes HTTP sadful
class CloneExperimentView(ExperimenterSingleExperimentView):
    def process_experiment(self, experiment):
        return experiment.clone()
    def render_to_response(self, context):
        return redirect('core:dashboard')

class ClearParticipantsExperimentView(ExperimenterSingleExperimentView):
    def process_experiment(self, experiment):
        experiment.participants.all().delete()
        return experiment
    def render_to_response(self, context):
        return redirect('core:dashboard')

@experimenter_required
def manage(request, pk=None):
    try :
        experiment = Experiment.objects.get(pk=pk)
# redirect to experiment specific management page?
        return redirect(experiment.management_url)
    except Experiment.DoesNotExist:
        logger.warning("Tried to manage non-existent experiment with id %s" %
                pk)


# FIXME: add data converter objects to write to csv, excel, etc.
@experimenter_required
def download_data(request, pk=None, file_type='csv'):
    try:
        experiment = Experiment.objects.get(pk=pk)
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name()
        writer = unicodecsv.UnicodeWriter(response)
        writer.writerow(['Group', 'Members'])
        for group in experiment.groups.all():
            writer.writerow(itertools.chain.from_iterable([[group], group.participants.all()]))
        for round_data in experiment.round_data.all():
            round_configuration = round_data.round_configuration
            # write out group-wide data values
            writer.writerow(['Group', 'Round', 'Data Parameter', 'Data Parameter Value'])
            for group_data_value in round_data.group_data_values.all():
                writer.writerow([group_data_value.group, round_configuration,
                    group_data_value.parameter.label, group_data_value.value])
            # write out specific participant data values for this round
            writer.writerow(['Participant', 'Round', 'Data Parameter', 'Data Parameter Value'])
            for participant_data_value in round_data.participant_data_values.all():
                writer.writerow([participant_data_value.participant_group_relationship, round_configuration,
                    participant_data_value.parameter.label, participant_data_value.value])
            if round_data.chat_messages.count() > 0:
# sort by group first, then time
                writer.writerow(['Group', 'Participant', 'Message', 'Time', 'Round'])
                for chat_message in round_data.chat_messages.order_by('participant_group_relationship__group', 'date_created'):
                    writer.writerow([chat_message.group, chat_message.participant, chat_message.message,
                        chat_message.date_created, round_configuration])
        return response
    except Experiment.DoesNotExist:
        error_message = "Tried to download non-existent experiment, id %s" % pk
        logger.warning(error_message)
        messages.warning(request, error_message)
        return redirect('core:dashboard')

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
        for group in experiment.groups.all():
            for participant in group.participants.all():
                group_sheet.write(current_row, 0, group)
                group_sheet.write(current_row, 1, participant)
            current_row += 1
        group_sheet.write(current_row, 0, 'Group')
        group_sheet.write(current_row, 1, 'Round')
        group_sheet.write(current_row, 2, 'Data Parameter')
        group_sheet.write(current_row, 3, 'Data Parameter Value')
        for group in experiment.groups.all():
            for data_value in group.data_values.all():
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
            experiment_func = getattr(experiment, experiment_action.replace('-', '_'), None)
            if experiment_func:
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
