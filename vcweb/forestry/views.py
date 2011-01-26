# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import is_participant, is_experimenter, Experiment, RoundConfiguration
from vcweb.core.decorators import participant_required, experimenter_required

import logging
logger = logging.getLogger(__name__)

@login_required
def index(request):
    if is_participant(request.user):
        return redirect('forestry:participant_index')
        #return render_to_response('forestry/participant-index.html', RequestContext(request))
    elif is_experimenter(request.user):
        ''' FIXME: should redirect to forestry-specific experimenter dashboard instead '''
        #return render_to_response('forestry/experimenter-index.html')
        return redirect('forestry:experimenter_index')
    else:
        logger.warning("user %s isn't an experimenter or participant" % request.user)
        return redirect('home')


@experimenter_required
def configure(request):
    return Http404()

@experimenter_required
def manage_experiment(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/manage-experiment.html', locals(), context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment available with id [%s]" % experiment_id)
        return redirect('core:experimenter_index')

@participant_required
def next_round(request, experiment_id=None):
    if is_participant(request.user):
        try:
            experiment = Experiment.objects.get(pk=experiment_id)
            return render_to_response('forestry/wait.html',
                    locals(),
                    context_instance=RequestContext(request))
        except Experiment.DoesNotExist:
            logger.warning("No experiment found with id %s" % experiment_id)
    return redirect('forestry:participant_index')


@participant_required
def participate(request, experiment_id=None):
    try:
        participant = request.user.participant
        experiment = Experiment.objects.get(pk=experiment_id)
        participant_group_relationship = participant.get_participant_group_relationship(experiment)
        return render_to_response(experiment.current_round_template,
                locals(),
                context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment with id [%s]" % experiment_id)
        return redirect('forestry:index')
