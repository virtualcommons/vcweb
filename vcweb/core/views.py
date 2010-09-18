# Create your views here.

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.forms import RegistrationForm, LoginForm
from vcweb.core.models import Participant, Experiment, Experimenter
import logging

logger = logging.getLogger("core-views")

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
                return redirect('core:experimenter-index' if hasattr(user, 'experimenter') else 'core:participant-index')
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
            institution = form.cleaned_data['institution']
            user = User.objects.create_user(email, email, password)
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            participant = Participant(institution=institution, user=user)
            participant.save()
            return redirect('core:profile')
    else:
        form = RegistrationForm()
        return render_to_response('registration/register.html', locals(), context_instance=RequestContext(request))

@login_required
def experimenter_index(request):
    user = request.user
    try:
        experimenter = user.experimenter
        experiments = Experiment.objects.filter(experimenter=experimenter)
        return render_to_response('experimenter-index.html', RequestContext(request, locals()))
    except Experimenter.DoesNotExist:
        return redirect('home')

@login_required
def participant_index(request):
    user = request.user
    try:
        participant = user.participant
        experiments = [ group.experiment for group in participant.group.all() ]
        return render_to_response('participant-index.html', RequestContext(request, locals()))
    except Participant.DoesNotExist:
        # add error message
        return redirect('home')

@login_required
def account_profile(request):
    return render_to_response('registration/profile.html', RequestContext(request))


@login_required
def configure(request, experiment_id):
    # lookup game instance id (or create a new one?)
    return render_to_response('configure.html', RequestContext(request))
