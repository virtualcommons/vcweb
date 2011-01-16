# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import is_participant, is_experimenter, Experiment, RoundConfiguration

import logging
logger = logging.getLogger(__name__)

@login_required
def index(request):
    if is_participant(request.user):
        return render_to_response('forestry/index.html', RequestContext(request))
    elif is_experimenter(request.user):
        ''' FIXME: should redirect to forestry-specific experimenter dashboard instead '''
        return redirect('core:experimenter-index')
    else:
        logger.warn("user %s isn't an experimenter or participant" % request.user)
        return redirect('core:index')

@login_required
def configure(request):
    return Http404()

@login_required
def experimenter(request, experiment_id=None):
    if experiment_id is None:
        logger.debug("No experiment id specified")
        return redirect('forestry:index')
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
        return redirect('forestry:index')
    try:
        participant = request.user.participant
    except AttributeError:
        logger.debug("logged in user %s wasn't a participant" % request.user)
        return redirect('index')
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        participant_group_relationship = participant.get_participant_group_relationship(experiment)
        return render_to_response(experiment.current_round_template,
                { 'experiment': experiment, 'participant_group': participant_group_relationship },
                context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment with id [%s]" % experiment_id)
        return redirect('forestry:index')
