# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import Experiment, is_participant, is_experimenter
import logging

logger = logging.getLogger('forestry.views')

@login_required
def index(request):
    if is_participant(request.user):
        return render_to_response('forestry/index.html', RequestContext(request))
    return redirect('experimenter')

@login_required
def configure(request):
    return Http404()

@login_required
def experimenter(request, experiment_id=None):
    if experiment_id is None:
        logger.debug("No experiment id specified")
        return redirect('index')

    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/experimenter.html',
                                  { 'experiment' : experiment },
                                  context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment available with id [%s]" % experiment_id)
        return redirect('core:experimenter-index')


@login_required
def participate(request, experiment_id=None):
    if experiment_id is None:
        logger.debug("No experiment id specified, redirecting to forestry index page.")
        return redirect('index')
    try:
        participant = request.user.participant
    except AttributeError:
        logger.debug("No participant available on logged in user %s" % request.user)
        return redirect('index')
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/participate.html',
                                  { 'participant': participant, 'experiment' : experiment },
                                  context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment with id [%s]" % experiment_id)
        return redirect('index')



