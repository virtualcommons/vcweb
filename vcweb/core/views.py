from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.forms import RegistrationForm, LoginForm, ParticipantAccountForm, ExperimenterAccountForm
from vcweb.core.models import Participant, Experiment, Institution, is_participant, is_experimenter
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
import hashlib
import base64
from datetime import datetime
import logging
from vcweb.core import unicodecsv
logger = logging.getLogger(__name__)

""" account registration / login / logout / profile views """

@login_required
def dashboard(request):
    if is_participant(request.user):
        return participant_index(request)
    elif is_experimenter(request.user):
        return experimenter_index(request)
    else:
        logger.warning("user %s isn't an experimenter or participant" % request.user)
        return redirect('home')

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
            email = form.cleaned_data['email']
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
""" participant home page """
@participant_required
def participant_index(request):
    participant = request.user.participant
    experiment_dict = {}
    for experiment in participant.experiments.all():
        if not experiment.experiment_metadata in experiment_dict:
            experiment_dict[experiment.experiment_metadata] = dict([(choice[0], list()) for choice in Experiment.STATUS_CHOICES])
        experiment_dict[experiment.experiment_metadata][experiment.status].append(experiment)

    logger.debug("experiment_dict %s" % experiment_dict)

    return render_to_response('participant-index.html', locals(), context_instance=RequestContext(request))

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
@experimenter_required
def experimenter_index(request):
    experiments = Experiment.objects.filter(experimenter=request.user.experimenter)
    return render_to_response('experimenter-index.html', locals(), context_instance=RequestContext(request))

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
def monitor(request, experiment_id=None):
    try :
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('monitor.html', locals(), context_instance=RequestContext(request))
# redirect to experiment specific management page?
    except Experiment.DoesNotExist:
        error_message = "Tried to monitor non-existent experiment (id %s)" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
        return redirect('core:dashboard')

@experimenter_required
def download_data_csv(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name()
        writer = unicodecsv.UnicodeWriter(response)
        writer.writerow(['Group', 'Members'])
        for group in experiment.groups.all():
            writer.writerow([group, '::'.join(group.participants.all())])
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
        response['Content-Disposition'] = 'attachment; filename=%s' % experiment.data_file_name('.xls')
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
