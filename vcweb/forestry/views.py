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
        logger.debug("logged in user %s wasn't a participant" % request.user)
        return redirect('index')
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response(get_template(experiment),
                                  { 'participant': participant, 'experiment' : experiment },
                                  context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment with id [%s]" % experiment_id)
        return redirect('index')

round_type_to_template = {
                          'INSTRUCTIONS' : lambda x: 'instructions.html',
                          'CHAT' : lambda x: 'chat.html',
                          'PRACTICE' : lambda x: 'practice.html',
                          'DEBRIEFING' : lambda x: 'debriefing.html',
                          'PLAY' : lambda x: 'participate.html',
                          'QUIZ': lambda x: x.quiz_template if x.quiz_template else 'quiz.html'
                          }

def get_template(experiment):
    round_configuration = experiment.current_round
    round_type = round_configuration.round_type
    return "%s/%s" % (experiment.namespace, round_type_to_template[round_type](round_configuration))







