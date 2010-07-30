# Create your views here.
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.decorators import *
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import Context, loader
from django.template.context import RequestContext
from vcweb.core.forms import RegistrationForm, LoginForm
from vcweb.core.models import Experimenter

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
                return redirect('experimenter-index' if user.experimenter else 'participant-index')
    else:
        form = LoginForm()
        return render_to_response('registration/login.html', locals(), context_instance=RequestContext(request))

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
    return render_to_response('experimenter-index.html', RequestContext(request))

def configure(request, game_instance_id):
# lookup game instance id (or create a new one?)
    t = loader.get_template('base_participant.html')
    c = RequestContext(request, {
        'main': "configuration of the experiment!",
        'username':"foo",

    })
    return HttpResponse(t.render(c))

def participant_index(request):
    # FIXME: check if logged in
    t = loader.get_template('participant-index.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))

