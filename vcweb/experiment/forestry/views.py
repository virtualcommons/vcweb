import logging

from django.http import Http404
from django.db import transaction
from django.shortcuts import render, get_object_or_404

from vcweb.core.decorators import group_required
from vcweb.core.http import JsonResponse, dumps
from vcweb.core.forms import SingleIntegerDecisionForm
from vcweb.core.models import (
    Experiment, ChatMessage, ParticipantGroupRelationship, RoundConfiguration, PermissionGroup)
from vcweb.experiment.forestry.models import (get_experiment_metadata, get_max_allowed_harvest_decision,
                                              get_resource_level, get_initial_resource_level, get_harvest_decision_dv,
                                              get_regrowth_dv, set_harvest_decision, get_average_harvest, GroupData,
                                              can_view_group_results)


logger = logging.getLogger(__name__)


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    participant = request.user.participant

    logger.debug(
        "handling participate request for %s and experiment %s", participant, experiment_id)

    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'),
                                   pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)

    if experiment.experiment_metadata != get_experiment_metadata() or pgr.participant != request.user.participant:
        raise Http404

    return render(request, experiment.participant_template, {
        'experiment': experiment,
        'participant_experiment_relationship': experiment.get_participant_experiment_relationship(participant),
        'participant_group_relationship': pgr,
        'experimentModelJson': dumps(get_view_model(experiment, pgr)),
    })


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def submit_harvest_decision(request, experiment_id=None):
    form = SingleIntegerDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(
            ParticipantGroupRelationship, pk=participant_group_id)
        harvest_decision = form.cleaned_data['integer_decision']
        submitted = form.cleaned_data['submitted']
        logger.debug("pgr %s harvested %s - final submission? %s",
                     pgr, harvest_decision, submitted)
        with transaction.atomic():
            round_data = experiment.current_round_data
            set_harvest_decision(
                pgr, harvest_decision, round_data, submitted=submitted)
            message = "%s harvested %s trees"
            experiment.log(message % (pgr.participant, harvest_decision))
            response_dict = {
                'success': True,
                'message': message % (pgr.participant_handle, harvest_decision),
            }
            return JsonResponse(response_dict)
    else:
        logger.debug("form was invalid: %s", form)
    for field in form:
        if field.errors:
            logger.debug("field %s had errors %s", field, field.errors)
    return JsonResponse({'success': False})


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'),
                                   pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(
        request.user.participant)
    return JsonResponse(get_view_model(experiment, pgr))


experiment_model_defaults = {
    'submitted': False,
    'chatEnabled': False,
    'resourceLevel': 0,
    'totalEarnings': 0,
    'groupEarnings': [],
    'maximumResourcesToDisplay': 20,
    'warningCountdownTime': 10,
    'harvestDecision': 0,
    'roundDuration': 60,
    'chatMessages': [],
    'myGroup': {
        'resourceLevel': 0,
        'regrowth': 0,
        'originalResourceLevel': 0,
        'averageHarvest': 0,
        'isResourceEmpty': 0,
    },
    'selectedHarvestDecision': False,
    'isInstructionsRound': False,
    'lastHarvestDecision': 0,
    'groupData': [],
    'regrowth': 0,
}


def get_view_model(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    previous_round = experiment.previous_round
    previous_round_data = experiment.get_round_data(
        round_configuration=previous_round, previous_round=True)

    experiment_model_dict = experiment.to_dict(
        include_round_data=False, default_value_dict=experiment_model_defaults)

    experiment_model_dict['timeRemaining'] = experiment.time_remaining
    experiment_model_dict['sessionId'] = current_round.session_id
    experiment_model_dict['maxHarvestDecision'] = get_max_allowed_harvest_decision(participant_group_relationship,
                                                                                   current_round_data, ec)
    experiment_model_dict['templateName'] = current_round.template_name
    experiment_model_dict['isPracticeRound'] = current_round.is_practice_round
    experiment_model_dict[
        'showTour'] = current_round.is_practice_round and not previous_round.is_practice_round
    experiment_model_dict[
        'participantGroupId'] = participant_group_relationship.pk

    # instructions round parameters
    if current_round.is_instructions_round:
        experiment_model_dict['isInstructionsRound'] = True
        experiment_model_dict['participantsPerGroup'] = ec.max_group_size
        # experiment_model_dict['regrowthRate'] = regrowth_rate
        experiment_model_dict[
            'initialResourceLevel'] = get_initial_resource_level(current_round)

    if current_round.is_playable_round or current_round.is_debriefing_round:

        experiment_model_dict['chatEnabled'] = current_round.chat_enabled

        own_group = participant_group_relationship.group
        own_resource_level = get_resource_level(own_group)
        experiment_model_dict['resourceLevel'] = own_resource_level

        # Create GroupData object to access group members data
        gd = GroupData(
            participant_group_relationship, previous_round_data, current_round_data)

        experiment_model_dict.update(gd.get_own_data())
        # Data of all the players in the same group of current logged in
        # participant
        experiment_model_dict['groupData'] = gd.get_group_data()

        regrowth = experiment_model_dict['regrowth'] = get_regrowth_dv(
            own_group, current_round_data).int_value
        logger.debug("The regrowth is %s", regrowth)

        experiment_model_dict['myGroup'] = {
            'resourceLevel': own_resource_level,
            'regrowth': regrowth,
            'originalResourceLevel': own_resource_level - regrowth,
            'averageHarvest': get_average_harvest(own_group, previous_round_data),
            'isResourceEmpty': own_resource_level == 0,
        }
        # If current round is debriefing round get the earnings of the participant depending upon the
        # type of round user completed
        if current_round.is_debriefing_round:
            if previous_round.is_practice_round:
                rounds = experiment.round_data_set.filter(
                    round_configuration__round_type=RoundConfiguration.RoundType.PRACTICE)
            else:
                rounds = experiment.round_data_set.filter(
                    round_configuration__round_type=RoundConfiguration.RoundType.REGULAR)

            experiment_model_dict['totalEarnings'] = gd.get_own_earnings(
                rounds, ec.exchange_rate)

            if can_view_group_results(current_round):
                experiment_model_dict['groupEarnings'] = gd.get_group_earnings(
                    rounds, ec.exchange_rate)

    # Participant group data parameters are only needed if this round is a data round
    # or the previous round was a data round
    if previous_round.is_playable_round or current_round.is_playable_round:

        harvest_decision = get_harvest_decision_dv(
            participant_group_relationship, current_round_data)
        experiment_model_dict['submitted'] = harvest_decision.submitted

        if harvest_decision.submitted:
            # user has already submit a harvest decision for this round
            experiment_model_dict[
                'harvestDecision'] = harvest_decision.int_value
            logger.debug("Already submitted, setting harvest decision to %s",
                         experiment_model_dict['harvestDecision'])

        experiment_model_dict['chatMessages'] = [
            cm.to_dict() for cm in ChatMessage.objects.for_group(own_group)]

    return experiment_model_dict
