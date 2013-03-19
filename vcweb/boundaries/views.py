from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from vcweb.core import dumps
from vcweb.core.decorators import participant_required
from vcweb.core.http import JsonResponse
from vcweb.core.models import (is_participant, is_experimenter, Experiment, ParticipantGroupRelationship,
        ParticipantExperimentRelationship, ChatMessage, ParticipantRoundDataValue)
from vcweb.boundaries.forms import HarvestDecisionForm
from vcweb.boundaries.models import (get_experiment_metadata, get_regrowth_rate, get_harvest_decision_parameter,
        get_cost_of_living, get_resource_level, get_initial_resource_level, get_total_storage, get_storage,
        get_last_harvest_decision, can_observe_other_group)
import logging
import random

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration').prefetch_related('group_set', 'experiment_configuration__round_configuration_set'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)
    if experiment.experiment_metadata != get_experiment_metadata() or pgr.participant != request.user.participant:
        raise Http404

# sends view model JSON to the template to be processed by knockout
    return render_to_response('boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'experiment': experiment,
        'participant_group_relationship': pgr,
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
                round_data=experiment.current_round_data, parameter=get_harvest_decision_parameter())
        # set harvest decision for participant
        # FIXME: inconsistency, GET returns HTML and POST return JSON..
        return JsonResponse(dumps({ 'success': True, 'experimentModelJson': get_view_model_json(experiment, pgr)}))
    for field in form:
        if field.errors:
            logger.debug("field %s had errors %s", field, field.errors)
    return JsonResponse(dumps({'success': False }))


def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    previous_round = experiment.previous_round
    previous_round_data = experiment.get_round_data(round_configuration=previous_round)

    experiment_model_dict = experiment.as_dict(include_round_data=False, attrs={})
    regrowth_rate = get_regrowth_rate(current_round)
    cost_of_living = get_cost_of_living(current_round)
    own_group = participant_group_relationship.group
    own_resource_level = 0
    last_harvest_decision = get_last_harvest_decision(participant_group_relationship, round_data=previous_round_data)
    experiment_model_dict['playerData'] = [{
        'id': pgr.participant_number,
        'lastHarvestDecision': last_harvest_decision,
        'storage': get_storage(pgr, current_round_data),
        } for pgr in own_group.participant_group_relationship_set.all()]
    experiment_model_dict['chatMessages'] = [{
        'pk': cm.pk,
        'participant_number': cm.participant_group_relationship.participant_number,
        'message': cm.string_value,
        'date_created': cm.date_created.strftime("%I:%M:%S")
        } for cm in ChatMessage.objects.for_group(own_group)]
    experiment_model_dict['initialResourceLevel'] = get_initial_resource_level(current_round)
    if not current_round.is_practice_round and can_observe_other_group(current_round):
        gr = GroupRelationship.objects.select_related('cluster').get(group=own_group)
        group_data = []
        for group in gr.cluster.group_set.all():
            if group != own_group:
                group_data.append({
                    'groupId': unicode(group),
                    'resourceLevel': resource_level,
                    'totalStorage': get_total_storage(group),
                    'regrowthRate': regrowth_rate,
                    'costOfLiving': cost_of_living,
                    })
        experiment_model_dict['groupData'] = group_data

# round / experiment configuration data
    experiment_model_dict['participantsPerGroup'] = ec.max_group_size
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['regrowthRate'] = regrowth_rate
    experiment_model_dict['costOfLiving'] = cost_of_living
    experiment_model_dict['participantNumber'] = participant_group_relationship.participant_number
    experiment_model_dict['participantGroupId'] = participant_group_relationship.pk
    experiment_model_dict['dollarsPerToken'] = ec.exchange_rate
    experiment_model_dict['chatEnabled'] = current_round.chat_enabled
# FIXME: defaults hard coded in for now
    experiment_model_dict['maxEarnings'] = 20.00
    experiment_model_dict['warningCountdownTime'] = 10

    experiment_model_dict['lastHarvestDecision'] = last_harvest_decision
    experiment_model_dict['storage'] = get_storage(participant_group_relationship, current_round_data)
    experiment_model_dict['resourceLevel'] = own_resource_level
# FIXME: these need to be looked up
    experiment_model_dict['maxHarvestDecision'] = 10
    experiment_model_dict['hasSubmit'] = False
    experiment_model_dict['practiceRound'] = round_configuration.is_practice_round
    experiment_model_dict['instructions'] = current_round.get_custom_instructions(session_number=get_session_number(current_round))
    experiment_model_dict.update(**kwargs)
    return dumps(experiment_model_dict)

def get_session_number(round_configuration):
    # FIXME: brittle but alternatives are messy and time consuming, refactor later
    if round_configuration.sequence_number > 22:
        return 2
    else:
        return 1
