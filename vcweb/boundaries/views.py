from django import forms
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.views.generic import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from vcweb.core.decorators import participant_required
from vcweb.core.json import dumps
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.views import ParticipantSingleExperimentMixin
from vcweb.boundaries.models import get_experiment_metadata, get_regrowth_rate, get_survival_cost
import logging

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related(), pk=experiment_id)
    if experiment.experiment_metadata != get_experiment_metadata():
        raise Http404
    participant_experiment_relationship = participant.get_participant_experiment_relationship(experiment)
    number_of_trees_per_row = 20
    max_width = number_of_trees_per_row * 30
    tree = trees['pine']
    resource_level = 100
    max_height = (resource_level / number_of_trees_per_row) * tree['height']
    number_of_resource_divs = range(0, resource_level / number_of_trees_per_row)
    resource_width = (resource_level % number_of_trees_per_row) * 30
# FIXME: this should always render the participate.html template and expose a
# JSON RoundConfiguration object to the page so the template knows what to render..?
    return render_to_response('boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'participant_experiment_relationship': participant_experiment_relationship,
        'experiment': experiment,
        'max_width': max_width,
        'max_height': max_height,
        'experimentModelJson': to_json(experiment, participant),
        },
        context_instance=RequestContext(request))


# FIXME: figure out the appropriate place for this
trees = {
        'deciduous': { 'name': 'deciduous-tree', 'height': 32 },
        'pine': {'name': 'pine-tree', 'height': 79 },
        }

def to_json(experiment, participant):
    pgr = participant.get_participant_group_relationship(experiment)
    group = pgr.group
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    experiment_model_dict = experiment.as_dict(include_round_data=False, attrs={})
    experiment_model_dict['participantsPerGroup'] = ec.max_group_size
    experiment_model_dict['numberOfRounds'] = ec.final_sequence_number
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['regrowthRate'] = get_regrowth_rate(current_round)
    experiment_model_dict['survivalCost'] = get_survival_cost(current_round)
    experiment_model_dict['participantNumber'] = pgr.participant_number
# FIXME: hard coded for now
    experiment_model_dict['maxHarvestDecision'] = 10
    experiment_model_dict['storedResources'] = 20
    experiment_model_dict['resourceLevel'] = 100
    experiment_model_dict['hasSubmit'] = False
    experiment_model_dict['practiceRound'] = False
    return dumps(experiment_model_dict)
