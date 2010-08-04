# Create your views here.

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.forms import RegistrationForm, LoginForm
from vcweb.core.models import Participant, GameInstance, Experimenter
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
            cleaned_data = form.cleaned_data
            # do something with cleaned data

            return redirect('core-index')
    else:
        form = RegistrationForm()
        return render_to_response('registration/register.html', locals(), context_instance=RequestContext(request))

@login_required
def experimenter_index(request):
    user = request.user
    try:
        experimenter = user.experimenter
        games = GameInstance.objects.filter(experimenter=experimenter)
        return render_to_response('experimenter-index.html', RequestContext(request, locals()))
    except Experimenter.DoesNotExist:
        return redirect('home')

@login_required
def participant_index(request):
    user = request.user
    try:
        participant = user.participant
        games = [ group.game_instance for group in participant.group.all() ]
        return render_to_response('participant-index.html', RequestContext(request, locals()))
    except Participant.DoesNotExist:
        # add error message
        return redirect('home')

@login_required
def account_profile(request):
    return redirect('home')


@login_required
def configure(request, game_instance_id):
    # lookup game instance id (or create a new one?)
    return render_to_response('configure.html', RequestContext(request))
