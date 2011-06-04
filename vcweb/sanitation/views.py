from vcweb.core.models import Experiment
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext

import logging
logger = logging.getLogger(__name__)

def configure(request, experiment_id=None):
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('sanitation/configure.html', {
        'experiment': experiment,
        },
        context_instance=RequestContext(request))

def consent(request, experiment):
    pass

def survey(request, experiment):
    pass

def quiz(request, experiment):
    pass

def instructions(request, experiment):
    pass

def play(request, experiment):
    pass

def participate(request, experiment_id=None):
# lookup participant's current location and then invoke the method named by the location
    participant = request.user.participant
# FIXME: this isn't implemented
    experiment = Experiment.objects.get(pk=experiment_id)
    current_location = participant.current_location # "consent", "survey", "quiz", "play", "instructions"
    if current_location in ["consent", "survey", "quiz", "play", "instructions"]:
        logger.debug("current location %s is valid", current_location)
# invoke current_location as a method and pass in the request and the experiment
        location_method = getattr(__name__, current_location)
        return location_method(request, experiment)
    logger.debug("Invalid location %s, redirecting to dashboard", current_location)
    return redirect('core:dashboard')

