# Create your views here.
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.decorators import participant_required, experimenter_required
from vcweb.forestry.models import get_resource_level, get_max_harvest_decision, get_forestry_experiment_metadata

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
def experimenter_index(request):
    experimenter = request.user.experimenter
    experiments = experimenter.experiments.all()
    return render_to_response('forestry/experimenter-index.html', locals(), context_instance=RequestContext(request))

@participant_required
def participant_index(request):
    participant = request.user.participant
    experiment_dict = {}
    for experiment in participant.experiments.filter(experiment_metadata=get_forestry_experiment_metadata()):
        if not experiment.status in experiment_dict:
            experiment_dict[experiment.status] = list()
        experiment_dict[experiment.status].append(experiment)

    return render_to_response('forestry/participant-index.html', locals(), context_instance=RequestContext(request))

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
def wait(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/wait.html',
                locals(),
                context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment found with id %s" % experiment_id)

@participant_required
def participate(request, experiment_id=None):
    try:
        participant = request.user.participant
        experiment = Experiment.objects.get(pk=experiment_id)
        if experiment.is_round_started:
            participant_group_relationship = participant.get_participant_group_relationship(experiment)
            resource_level = get_resource_level(participant_group_relationship.group)
            logger.debug("resource level is: %s" % resource_level)
            max_harvest_decision = get_max_harvest_decision(resource_level.value)
            logger.debug("max harvest decision: %s" % max_harvest_decision)
            return render_to_response(experiment.current_round_template,
                    locals(),
                    context_instance=RequestContext(request))
        else:
# the experiment hasn't started yet, just redirect to the instructions for now.. we
# should redirect to a proper waiting page later.
            messages.info(request, 'The experiment has not yet started.')
            return render_to_response(experiment.current_round_template, locals())
    except Experiment.DoesNotExist:
        logger.warning("No experiment with id [%s]" % experiment_id)
        return redirect('forestry:index')

