from django import forms
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.views.generic import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from vcweb.core.decorators import participant_required
from vcweb.core.json import dumps
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.views import ParticipantSingleExperimentMixin
from vcweb.boundaries.forms import HarvestDecisionForm
from vcweb.boundaries.models import (get_experiment_metadata, get_regrowth_rate, get_survival_cost, get_resource_level,
        get_total_storage)
import logging
import random

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    form = HarvestDecisionForm(request.POST or None)
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related(), pk=experiment_id)
    if experiment.experiment_metadata != get_experiment_metadata():
        raise Http404
    if form.is_valid():
        logger.debug("handing POST request, cleaned data: %s", form.cleaned_data)
        # set harvest decision for participant
        # FIXME: is it bad practice to have GET return HTML and POST return JSON?
        # send updated experiment json?
        return HttpResponse(dumps({ 'success': True, 'experimentModelJson': to_json(experiment, participant, hasSubmit=True)}))
# FIXME: still need to look up participant group relationship and throw 404 if invalid

# sends view model JSON to the template to be processed by knockout
    return render_to_response('boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'experiment': experiment,
        'experimentModelJson': to_json(experiment, participant),
        },
        context_instance=RequestContext(request))

def to_json(experiment, participant, **kwargs):
    pgr = participant.get_participant_group_relationship(experiment)
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    experiment_model_dict = experiment.as_dict(include_round_data=False, attrs={})
    group_data = []
    player_data = []
    regrowth_rate = get_regrowth_rate(current_round)
    survival_cost = get_survival_cost(current_round)
    for group in experiment.group_set.all():
        group_data.append({
            'groupId': unicode(group),
            'resourceLevel': get_resource_level(group),
            'totalStorage': get_total_storage(group),
            'regrowthRate': regrowth_rate,
            'survivalCost': survival_cost,
            })

    for participant_group_relationship in pgr.group.participant_group_relationship_set.all():
        player_data.append({
            'id': participant_group_relationship.participant_number,
            'lastHarvestDecision': random.randint(0, 10),
            'storage': random.randint(0, 30),
            })
    experiment_model_dict['groupData'] = group_data
    experiment_model_dict['otherGroupResourceLevel'] = random.randint(50, 100)
    experiment_model_dict['otherGroupAverageHarvest'] = random.uniform(0, 10)
    experiment_model_dict['otherGroupAverageStorage'] = random.uniform(10, 30)

    experiment_model_dict['playerData'] = player_data
    experiment_model_dict['participantsPerGroup'] = ec.max_group_size
    experiment_model_dict['numberOfRounds'] = ec.final_sequence_number
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['regrowthRate'] = regrowth_rate
    experiment_model_dict['survivalCost'] = survival_cost
    experiment_model_dict['participantNumber'] = pgr.participant_number
    experiment_model_dict['participantGroupId'] = pgr.pk
# FIXME: defaults hard coded in for now
    experiment_model_dict['lastHarvestDecision'] = 5
    experiment_model_dict['maxHarvestDecision'] = 10
    experiment_model_dict['storage'] = 20
    experiment_model_dict['resourceLevel'] = 100
    experiment_model_dict['hasSubmit'] = False
    experiment_model_dict['practiceRound'] = False
    experiment_model_dict.update(**kwargs)
    return dumps(experiment_model_dict)
