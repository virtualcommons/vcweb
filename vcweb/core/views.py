"""
vcweb.core views
"""

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.forms import RegistrationForm, LoginForm
from vcweb.core.models import Participant, Experiment, Experimenter, Institution, is_participant, is_experimenter
from vcweb.core.queue import broadcast_chat
from vcweb.core.decorators import anonymous_required, experimenter_required, participant_required
import logging

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
                return render_to_response('registration/login.html', locals(), context_instance=RequestContext(request))
            else:
                auth.login(request, user)
                # check if user is an experimenter
                return redirect('core:dashboard')
    else:
        form = LoginForm()
        return render_to_response('registration/login.html', locals(), context_instance=RequestContext(request))

def logout(request):
    auth.logout(request)
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
            logger.debug("form had errors: %s", form.errors)
    else:
        form = RegistrationForm()

    return render_to_response('registration/register.html', locals(), context_instance=RequestContext(request))

@login_required
def account_profile(request):
    return render_to_response('registration/profile.html', RequestContext(request))

''' participant views '''
""" participant home page """
@participant_required
def participant_index(request):
    participant = request.user.participant
    experiments = participant.experiments.all()
    return render_to_response('participant-index.html', locals(), RequestContext(request))

@login_required
def instructions(request, experiment_id=None, namespace=None):
    if experiment_id:
        experiment = Experiment.objects.get(pk=experiment_id)
    elif namespace:
        experiment = Experiment.objects.get(experiment_metadata__namespace=namespace)

    if not experiment:
        logger.warning("Tried to request instructions for id %s or namespace %s" % (experiment_id, namespace))
        return redirect('home')

    return render_to_response(experiment.get_template_path('welcome-instructions.html'), locals(), RequestContext(request))



"""
experimenter views
FIXME: add has_perms authorization to ensure that only experimenters can access
these.
"""
@experimenter_required
def experimenter_index(request):
    experiments = Experiment.objects.filter(experimenter=request.user.experimenter)
    return render_to_response('experimenter-index.html', locals(), RequestContext(request))

@experimenter_required
def configure(request, experiment_id=None):
    # lookup game instance id (or create a new one?)
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('configure.html', locals(), RequestContext(request))

@experimenter_required
def monitor(request, experiment_id=None):
    try :
        experiment = Experiment.objects.get(pk=experiment_id)
# test server push
        broadcast_chat(experiment, 'You are being monitored by %s' % request.user.experimenter)
        return render_to_response('monitor.html', locals(), RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("Tried to monitor non-existent experiment with id %s" %
                experiment_id)



@experimenter_required
def start_experiment(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        experiment.start()
        return redirect('core:manage_experiment')
    except Experiment.DoesNotExist:
        pass
        logger.warning("tried to start an experiment that doesn't exist (id: %s)" % experiment_id)
        return redirect('core:experimenter_index')


