from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from vcweb.core import dumps
from vcweb.core.decorators import participant_required
from vcweb.core.models import (is_participant, is_experimenter, Experiment, ParticipantGroupRelationship,
        ParticipantExperimentRelationship, ChatMessage, ParticipantRoundDataValue)
from vcweb.boundaries.forms import HarvestDecisionForm
from vcweb.boundaries.models import (get_experiment_metadata, get_regrowth_rate, get_harvest_decision_parameter,
        get_cost_of_living, get_resource_level, get_initial_resource_level, get_total_storage, get_storage)
import logging
import random

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration').prefetch_related('group_set', 'experiment_configuration__round_configuration_set'), pk=experiment_id)
    per = get_object_or_404(ParticipantExperimentRelationship.objects.select_related('participant'),
            experiment=experiment, participant=participant)
    pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group', 'participant__user').prefetch_related('group__participant_group_relationship_set'),
            group__experiment=experiment,
            participant=participant)
    if experiment.experiment_metadata != get_experiment_metadata() or pgr.participant != request.user.participant:
        raise Http404

# sends view model JSON to the template to be processed by knockout
    return render_to_response('boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'participant_experiment_relationship': per,
        'experimentModelJson': get_view_model_json(experiment, pgr),
        },
        context_instance=RequestContext(request))

@participant_required
def submit_harvest_decision(request, experiment_id=None):
    form = HarvestDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        logger.debug("handing POST request, cleaned data: %s", form.cleaned_data)
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        harvest_decision = form.cleaned_data['harvest_decision']
        ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr, int_value=harvest_decision,
                round_data=experiment.current_round_data(), parameter=get_harvest_decision_parameter())
        # set harvest decision for participant
        # FIXME: inconsistency, GET returns HTML and POST return JSON..
        return HttpResponse(dumps({ 'success': True, 'experimentModelJson': get_view_model_json(experiment, pgr)}))


def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    experiment_model_dict = experiment.as_dict(include_round_data=False, attrs={})
    group_data = []
    player_data = []
    regrowth_rate = get_regrowth_rate(current_round)
    cost_of_living = get_cost_of_living(current_round)
    own_group = participant_group_relationship.group
    own_resource_level = 0
    for group in experiment.group_set.all():
        resource_level = get_resource_level(group)
        if group == own_group:
            own_resource_level = resource_level
        group_data.append({
            'groupId': unicode(group),
            'resourceLevel': resource_level,
            'totalStorage': get_total_storage(group),
            'regrowthRate': regrowth_rate,
            'costOfLiving': cost_of_living,
            })

    for pgr in own_group.participant_group_relationship_set.all():
        player_data.append({
            'id': pgr.participant_number,
            'lastHarvestDecision': random.randint(0, 10),
            'storage': get_storage(pgr, current_round_data),
            })

    experiment_model_dict['chatMessages'] = [
            { 'pk': cm.pk,
                'participant_number': cm.participant_group_relationship.participant_number,
                'message': cm.string_value,
                'date_created': cm.date_created.strftime("%I:%M:%S")
                }
            for cm in ChatMessage.objects.for_group(own_group)
            ]
    experiment_model_dict['initialResourceLevel'] = get_initial_resource_level(current_round)
    experiment_model_dict['groupData'] = group_data
    experiment_model_dict['otherGroupResourceLevel'] = random.randint(50, 100)
    experiment_model_dict['otherGroupAverageHarvest'] = random.uniform(0, 10)
    experiment_model_dict['otherGroupAverageStorage'] = random.uniform(10, 30)

    experiment_model_dict['playerData'] = player_data
    experiment_model_dict['participantsPerGroup'] = ec.max_group_size
    experiment_model_dict['numberOfRounds'] = ec.final_sequence_number
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['regrowthRate'] = regrowth_rate
    experiment_model_dict['costOfLiving'] = cost_of_living
    experiment_model_dict['participantNumber'] = pgr.participant_number
    experiment_model_dict['participantGroupId'] = pgr.pk
# FIXME: defaults hard coded in for now
    experiment_model_dict['dollarsPerToken'] = 0.20
    experiment_model_dict['maxEarnings'] = 20.00
    experiment_model_dict['warningCountdownTime'] = 10

# FIXME: these need to be looked up
    experiment_model_dict['lastHarvestDecision'] = 5
    experiment_model_dict['maxHarvestDecision'] = 10
    experiment_model_dict['storage'] = 20
    experiment_model_dict['resourceLevel'] = own_resource_level
    experiment_model_dict['hasSubmit'] = False
    experiment_model_dict['practiceRound'] = False
    experiment_model_dict['instructions'] = current_round.get_custom_instructions(session_number=get_session_number(current_round))
    experiment_model_dict.update(**kwargs)
    return dumps(experiment_model_dict)

def get_session_number(round_configuration):
    # FIXME: brittle but alternatives are messy and time consuming, refactor later
    if round_configuration.sequence_number > 22:
        return 2
    else:
        return 1
