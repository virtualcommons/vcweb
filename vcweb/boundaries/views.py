from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from vcweb.core import dumps
from vcweb.core.decorators import participant_required
from vcweb.core.http import JsonResponse
from vcweb.core.models import (Experiment, ParticipantGroupRelationship, ChatMessage, GroupRelationship)
from vcweb.boundaries.forms import SingleIntegerDecisionForm
from vcweb.boundaries.models import (get_experiment_metadata, get_regrowth_rate, get_max_allowed_harvest_decision,
        get_cost_of_living, get_resource_level, get_initial_resource_level, get_total_storage, get_storage,
        get_last_harvest_decision, get_harvest_decision_dv, set_harvest_decision, can_observe_other_group, get_player_status)

import logging
logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration').prefetch_related('group_set', 'experiment_configuration__round_configuration_set'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)
    if experiment.experiment_metadata != get_experiment_metadata() or pgr.participant != request.user.participant:
        raise Http404
    return render(request, 'boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'experiment': experiment,
        'participant_experiment_relationship': experiment.get_participant_experiment_relationship(participant),
        'participant_group_relationship': pgr,
        'experimentModelJson': get_view_model_json(experiment, pgr),
        })

@participant_required
def submit_harvest_decision(request, experiment_id=None):
    form = SingleIntegerDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        harvest_decision = form.cleaned_data['integer_decision']
        set_harvest_decision(pgr, harvest_decision, experiment.current_round_data, submitted=True)
        message = "%s harvested %s trees"
        experiment.log(message % (pgr.participant, harvest_decision))
        return JsonResponse(dumps({ 'success': True, 'experimentModelJson': get_view_model_json(experiment, pgr),
            'message': message % (pgr.participant_handle, harvest_decision)}))
    else:
        logger.debug("form was invalid: %s", form)
    for field in form:
        if field.errors:
            logger.debug("field %s had errors %s", field, field.errors)
    return JsonResponse(dumps({'success': False }))

@participant_required
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(request.user.participant)
    logger.debug("getting view model for participant: %s", pgr)
    return JsonResponse(get_view_model_json(experiment, pgr))

experiment_model_defaults = {
        'submitted': False,
        'chatEnabled': False,
        'resourceLevel': 0,
        'maxEarnings': 20.00,
        'maximumResourcesToDisplay': 20,
        'warningCountdownTime': 10,
        'harvestDecision': 0,
        'chatMessages': [],
        'instructionsRound': False,
        }
# FIXME: need to distinguish between instructions / welcome rounds and practice/regular rounds
def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    previous_round = experiment.previous_round
    previous_round_data = experiment.get_round_data(round_configuration=previous_round)
    experiment_model_dict = experiment.to_dict(include_round_data=False, default_value_dict=experiment_model_defaults)

# round / experiment configuration data
    experiment_model_dict['roundDuration'] = current_round.duration
    experiment_model_dict['timeRemaining'] = experiment.time_remaining
    regrowth_rate = get_regrowth_rate(current_round)
    cost_of_living = get_cost_of_living(current_round)
    experiment_model_dict['costOfLiving'] = cost_of_living
    experiment_model_dict['maxHarvestDecision'] = get_max_allowed_harvest_decision(participant_group_relationship, current_round_data, ec)
# instructions round parameters
    if current_round.is_instructions_round:
        experiment_model_dict['instructionsRound'] = True
        experiment_model_dict['participantsPerGroup'] = ec.max_group_size
        experiment_model_dict['regrowthRate'] = regrowth_rate
        experiment_model_dict['initialResourceLevel'] = get_initial_resource_level(current_round)

    experiment_model_dict['participantNumber'] = participant_group_relationship.participant_number
    experiment_model_dict['participantGroupId'] = participant_group_relationship.pk
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['practiceRound'] = current_round.is_practice_round

    if current_round.is_regular_round:
        experiment_model_dict['chatEnabled'] = current_round.chat_enabled

    # FIXME: these need to be added so KO doesn't get unhappy when we switch templates from instructions rounds to
    # practice rounds.
    own_group = participant_group_relationship.group
    own_resource_level = get_resource_level(own_group)
    last_harvest_decision = get_last_harvest_decision(participant_group_relationship, round_data=previous_round_data)
    experiment_model_dict['playerData'] = [{
        'id': pgr.participant_number,
        'lastHarvestDecision': get_last_harvest_decision(pgr, round_data=previous_round_data),
        'alive': get_player_status(pgr, current_round_data),
        'storage': get_storage(pgr, current_round_data),
        } for pgr in own_group.participant_group_relationship_set.all()]
    # FIXME: redundancy with playerData
    experiment_model_dict['lastHarvestDecision'] = last_harvest_decision
    experiment_model_dict['storage'] = get_storage(participant_group_relationship, current_round_data)
    experiment_model_dict['resourceLevel'] = own_resource_level
    experiment_model_dict['alive'] = get_player_status(participant_group_relationship, current_round_data)
    # participant group data parameters are only needed if this round is a data round or the previous round was a data round
    if previous_round.is_playable_round or current_round.is_playable_round:
        harvest_decision = get_harvest_decision_dv(participant_group_relationship, current_round_data)
        experiment_model_dict['submitted'] = harvest_decision.submitted
        if harvest_decision.submitted:
            # user has already submit a harvest decision this round
            experiment_model_dict['harvestDecision'] = harvest_decision.int_value
            logger.debug("already submitted, setting harvest decision to %s", experiment_model_dict['harvestDecision'])

        experiment_model_dict['chatMessages'] = [{
            'pk': cm.pk,
            'participant_number': cm.participant_group_relationship.participant_number,
            'message': cm.string_value,
            'date_created': cm.date_created.strftime("%I:%M:%S")
            } for cm in ChatMessage.objects.for_group(own_group)]
        experiment_model_dict['canObserveOtherGroup'] = can_observe_other_group(current_round)
        if not current_round.is_practice_round and experiment_model_dict['canObserveOtherGroup']:
            gr = GroupRelationship.objects.select_related('cluster').get(group=own_group)
            group_data = []
            for group in gr.cluster.group_set.all():
                if group != own_group:
                    group_data.append({
                        'groupId': unicode(group),
                        'resourceLevel': get_resource_level(group),
                        'totalStorage': get_total_storage(group),
                        'regrowthRate': regrowth_rate,
                        'costOfLiving': cost_of_living,
                        })
            experiment_model_dict['groupData'] = group_data

# FIXME: defaults hard coded in for now
    experiment_model_dict['instructions'] = current_round.get_custom_instructions()
    return dumps(experiment_model_dict)
