from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from django.utils.decorators import method_decorator
from django.views.generic import ListView, FormView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from vcweb.core.forms import RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm
from vcweb.core.models import Participant, Experiment, Institution, is_participant, is_experimenter
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
import hashlib
import base64
from datetime import datetime
import logging
from vcweb.core import unicodecsv
import itertools
logger = logging.getLogger(__name__)

""" account registration / login / logout / profile views """

def _get_experiment(request, experiment_id):
    experiment = Experiment.objects.get(pk=experiment_id)
    if request.user.experimenter == experiment.experimenter:
        return experiment
    raise Experiment.DoesNotExist("Sorry, %s - you do not have access to experiment %s" % (experiment.experimenter, experiment_id))

class AnonymousMixin(object):
    @method_decorator(anonymous_required)
    def dispatch(self, *args, **kwargs):
        return super(AnonymousMixin, self).dispatch(*args, **kwargs)

class Dashboard(ListView, TemplateResponseMixin):
    context_object_name = 'experiments'
    def get_template_names(self):
        user = self.request.user
        if is_experimenter(user):
            return ['experimenter-dashboard.html']
        else:
            return ['participant-dashboard.html']
    def get_queryset(self):
        user = self.request.user
        if is_experimenter(user):
            return Experiment.objects.filter(experimenter__pk=self.request.user.experimenter.pk)
        else:
            experiment_dict = {}
            for experiment in user.participant.experiments.exclude(status__in=(Experiment.INACTIVE, Experiment.PAUSED, Experiment.COMPLETED)):
                if not experiment.experiment_metadata in experiment_dict:
                    experiment_dict[experiment.experiment_metadata] = dict([(choice[0], list()) for choice in Experiment.STATUS_CHOICES])
                experiment_dict[experiment.experiment_metadata][experiment.status].append(experiment)
                logger.debug("experiment_dict %s" % experiment_dict)
            return experiment_dict

class LoginView(FormView, AnonymousMixin):
    form_class = LoginForm
    template_name = 'registration/login.html'

    def form_valid(self, form):
        request = self.request
        user = form.user_cache
        auth.login(request, user)
        sha1 = hashlib.sha1()
        sha1.update("%s%i%s" % (user.email, user.pk, datetime.now()))
        request.session['authentication_token'] = base64.urlsafe_b64encode(sha1.digest())
        return super(LoginView, self).form_valid(form)

    def get_success_url(self):
        return_url = self.request.GET.get('next')
        return return_url if return_url else reverse('core:dashboard')

@anonymous_required()
def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            email = cleaned_data['email']
            password = cleaned_data['password']
            user = auth.authenticate(username=email, password=password)
            if user is None:
                logger.debug("user " + email + " failed to authenticate.")
                form.errors['password'] = form.error_class(['Your password is incorrect.'])
            else:
                return_url = request.GET.get('next')
                auth.login(request, user)
                sha1 = hashlib.sha1()
                sha1.update("%s%i%s" % (email, user.pk, datetime.now()))
                request.session['authentication_token'] = base64.urlsafe_b64encode(sha1.digest())
                return redirect( return_url if return_url else 'core:dashboard')
    else:
        form = LoginForm()
    return render_to_response('registration/login.html', locals(), context_instance=RequestContext(request))

def logout(request):
    auth.logout(request)
    request.session['authentication_token'] = None
    return redirect('home')

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            institution_string = form.cleaned_data['institution']
            institution, created = Institution.objects.get_or_create(name=institution_string)
            user = User.objects.create_user(email, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            participant = Participant.objects.create(user=user, institution=institution)
            logger.debug("Creating new participant: %s" % participant)
            auth.login(request, auth.authenticate(username=email, password=password))
            return redirect('core:dashboard')
    else:
        form = RegistrationForm()
    return render_to_response('registration/register.html', { 'form': form }, context_instance=RequestContext(request))

@login_required
def account_profile(request):
    if is_participant(request.user):
        form = ParticipantAccountForm(instance=request.user.participant)
    else:
        form = ExperimenterAccountForm(instance=request.user.experimenter)
    return render_to_response('registration/profile.html', { 'form': form }, context_instance=RequestContext(request))

''' participant views '''
class ParticipantMixin(object):
    @method_decorator(participant_required)
    def dispatch(self, *args, **kwargs):
        return super(ParticipantMixin, self).dispatch(*args, **kwargs)

@login_required
def instructions(request, experiment_id=None, namespace=None):
    if experiment_id:
        experiment = Experiment.objects.get(pk=experiment_id)
    elif namespace:
        experiment = Experiment.objects.get(experiment_metadata__namespace=namespace)

    if not experiment:
        logger.warning("Tried to request instructions for id %s or namespace %s" % (experiment_id, namespace))
        return redirect('home')

    return render_to_response(experiment.get_template_path('instructions.html'), locals(), context_instance=RequestContext(request))


"""
experimenter views
FIXME: add has_perms authorization to ensure that only experimenters can access
these.
"""
class ExperimenterMixin(object):
    def _get_experiment(self, request, experiment_id):
        experiment = Experiment.objects.get(pk=experiment_id)
        if request.user.experimenter.pk == experiment.experimenter.pk:
            return experiment
        raise Experiment.DoesNotExist("Sorry, you do not appear to have access to %s" % experiment)

    @method_decorator(experimenter_required)
    def dispatch(self, *args, **kwargs):
        return super(ExperimenterMixin, self).dispatch(*args, **kwargs)


@experimenter_required
def configure(request, experiment_id=None):
    # lookup game instance id (or create a new one?)
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('configure.html', locals(), context_instance=RequestContext(request))

@experimenter_required
def manage(request, experiment_id=None):
    try :
        experiment = Experiment.objects.get(pk=experiment_id)
# redirect to experiment specific management page?
        return redirect(experiment.management_url)
    except Experiment.DoesNotExist:
        logger.warning("Tried to manage non-existent experiment with id %s" %
                experiment_id)

@experimenter_required
def clone(request, experiment_id=None, count=0):
    try:
        experiment = _get_experiment(request, experiment_id)
        cloned_experiment = experiment.clone()
        if count > 0:
            cloned_experiment.setup_test_participants(count=count)
        logger.debug("cloned experiment: %s" % cloned_experiment)
    except Experiment.DoesNotExist:
        error_message = "Tried to monitor non-existent experiment (id %s)" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
    return redirect('core:dashboard')

@experimenter_required
def add_participants(request, experiment_id=None, count=0):
    try:
        experiment = _get_experiment(request, experiment_id)
        count = int(count)
        if count > 0:
            experiment.setup_test_participants(count=count)
    except Experiment.DoesNotExist:
        error_message = "Tried to monitor non-existent experiment (id %s)" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
    return redirect('core:dashboard')

@experimenter_required
def clear_participants(request, experiment_id=None):
    try:
        experiment = _get_experiment(request, experiment_id)
        if experiment.participants.count() > 0:
            experiment.participants.all().delete()
    except Experiment.DoesNotExist:
        error_message = "Tried to monitor non-existent experiment (id %s)" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
    return redirect('core:dashboard')


@experimenter_required
def monitor(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        if request.user.experimenter.pk == experiment.experimenter.pk:
            return render_to_response('monitor.html', locals(), context_instance=RequestContext(request))
# redirect to experiment specific management page?
    except Experiment.DoesNotExist:
        error_message = "Tried to monitor non-existent experiment (id %s)" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
    return redirect('core:dashboard')

# FIXME: add data converter objects to write to csv, excel, etc.
@experimenter_required
def download_data(request, experiment_id=None, file_type='csv'):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
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
    except Experiment.DoesNotExist as e:
        error_message = "Tried to download non-existent experiment, id %s" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
        return redirect('core:dashboard')

@experimenter_required
def download_data_excel(request, experiment_id=None):
    import xlwt
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
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
def experiment_controller(request, experiment_id=None, experiment_action=None):
    try:
        experimenter = request.user.experimenter
        experiment = Experiment.objects.get(pk=experiment_id)
# TODO: provide experimenter access to other users besides the creator of the
# experiment?
        if experimenter.pk == experiment.experimenter.pk:
            experiment_func = getattr(experiment, experiment_action.replace('-', '_'), None)
            if experiment_func:
                # pass params?  start_round() takes a sender for instance..
                experiment_func()
                return redirect('core:monitor_experiment', experiment_id=experiment_id)
            else:
                error_message = "Invalid experiment action: You ({experimenter}) tried to invoke {experiment_action} on {experiment}".format(
                      experimenter=experimenter, experiment_action=experiment_action, experiment=experiment)
        else:
            error_message = "Access denied for {experimenter}: You do not have permission to invoke {experiment_action} on {experiment}".format(
                  experimenter=experimenter, experiment_action=experiment_action, experiment=experiment)

    except Experiment.DoesNotExist:
       error_message = 'Could not invoke {experiment_action} on a non-existent experiment (id: {experiment_id}, experimenter: {experimenter})'.format(
             experimenter=experimenter, experiment_action=experiment_action, experiment_id=experiment_id)

    logger.warning(error_message)
    messages.warning(request, error_message)
    return redirect('core:dashboard')
