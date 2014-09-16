from collections import defaultdict
import random
import logging

from django.shortcuts import get_object_or_404, render

from vcweb.core.decorators import group_required
from vcweb.core import dumps
from vcweb.core.forms import SingleIntegerDecisionForm
from vcweb.core.http import JsonResponse
from vcweb.core.models import (
    Experiment, ParticipantGroupRelationship, RoundConfiguration, ParticipantRoundDataValue, PermissionGroup)
from vcweb.experiment.broker.models import (get_max_harvest_hours, set_harvest_decision, set_conservation_decision, get_harvest_decision,
                                            get_conservation_decision, get_payoff, get_chat_within_group_parameter, get_chat_between_group_parameter,
                                            get_participant_link_parameter)
from vcweb.experiment.broker.forms import ChatPreferenceForm


logger = logging.getLogger(__name__)


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def submit_chat_preferences(request, experiment_id=None):
    form = ChatPreferenceForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        logger.debug(
            "handling POST request, cleaned data: %s", form.cleaned_data)
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(
            ParticipantGroupRelationship, pk=participant_group_id)
        round_data = experiment.current_round_data
        chat_within_group = form.cleaned_data['chat_within_group']
        chat_between_group = form.cleaned_data['chat_between_group']
        pgr.set_data_value(parameter=get_chat_within_group_parameter(
        ), value=chat_within_group, round_data=round_data)
        if chat_between_group:
            related_group = pgr.group.get_related_group()
            pgr.set_data_value(parameter=get_chat_between_group_parameter(
            ), value=related_group.pk, round_data=round_data)

        ncwg = ParticipantRoundDataValue.objects.filter(
            parameter=get_chat_within_group_parameter(), round_data=round_data, submitted=True).count()
        ncbg = ParticipantRoundDataValue.objects.filter(
            parameter=get_chat_between_group_parameter(), round_data=round_data, submitted=True).count()
        np = experiment.participant_set.count()
        response_dict = {
            'success': True,
            'all_participants_submitted': False,
        }
        if ncwg == np and ncbg == np:
            logger.debug("calculating participant participant linkages")
            # everyone submitted a chat preference decision, create participant
            # linkages between groups
            between_group_dvs = ParticipantRoundDataValue.objects.filter(
                parameter=get_chat_between_group_parameter(), round_data=round_data, submitted=True)
            group_to_participants = defaultdict(list)
            for dv in between_group_dvs:
                group_to_participants[dv.participant_group_relationship.group].append(
                    (dv.participant_group_relationship, dv.value))
            [random.shuffle(v) for v in group_to_participants.values()]
            for group, participant_list in group_to_participants.items():
                for item in participant_list:
                    (pgr, target_group) = item
                    logger.debug(
                        "pgr %s wants to talk to %s", pgr, target_group)
                    willing_participants = group_to_participants[target_group]
                    if willing_participants:
                        (wpgr, wpgr_group) = willing_participants.pop()
                        logger.debug(
                            "creating edges between %s -> %s", pgr, wpgr)
                        # create two edges between these two participants
                        pgr.set_data_value(
                            parameter=get_participant_link_parameter(), round_data=round_data, value=wpgr.pk)
                        wpgr.set_data_value(
                            parameter=get_participant_link_parameter(), round_data=round_data, value=pgr.pk)
                    else:
                        # no more willing participants, break to outer loop
                        break

            response_dict['all_participants_submitted'] = True
        return JsonResponse(dumps(response_dict))
    return JsonResponse(dumps({'success': False}))


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def submit_decision(request, experiment_id=None):
    form = SingleIntegerDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        logger.debug(
            "handing POST request, cleaned data: %s", form.cleaned_data)
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(
            ParticipantGroupRelationship, pk=participant_group_id)
        harvest_hours = form.cleaned_data['integer_decision']
        conservation_hours = get_max_harvest_hours(experiment) - harvest_hours
        round_data = experiment.current_round_data
        set_harvest_decision(pgr, harvest_hours, round_data=round_data)
        set_conservation_decision(
            pgr, conservation_hours, round_data=round_data)
        return JsonResponse(dumps({'success': True, 'experimentModelJson': get_view_model_json(experiment, pgr)}))
    for field in form:
        if field.errors:
            logger.debug("field %s had errors %s", field, field.errors)
    return JsonResponse(dumps({'success': False}))


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, group__experiment=experiment,
                                                       participant=participant)

    return render(request, 'broker/participate.html', {
        'experiment': experiment,
        'participant_experiment_relationship': experiment.get_participant_experiment_relationship(participant),
        'participant_group_relationship': participant_group_relationship,
        'experimentModelJson': get_view_model_json(experiment, participant_group_relationship),
    })


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    participant_group_relationship = get_object_or_404(
        ParticipantGroupRelationship, pk=request.GET.get('participant_group_id'))
    return JsonResponse(get_view_model_json(experiment, participant_group_relationship))

experiment_model_defaults = {
    'chatEnabled': True,
    'maxHarvestDecision': 10,
    'maxEarnings': 20.00,
    'showChatRooms': True,
    'harvestDecision': 0,
    'betweenGroupChatMessages': [],
    'withinGroupChatMessages': [],
}


def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    experiment_model_dict = experiment.to_dict(
        include_round_data=False, default_value_dict=experiment_model_defaults)
    group = participant_group_relationship.group
    experiment_configuration = experiment.experiment_configuration
    round_configuration = experiment.current_round
    previous_round_data = experiment.get_round_data(
        round_configuration=experiment.previous_round)
    round_data = experiment.current_round_data

# experiment data
    experiment_model_dict[
        'participantGroupId'] = participant_group_relationship.pk
# experiment configuration data
    experiment_model_dict['localBonus'] = experiment_configuration.get_parameter_value(
        name='group_local_bonus', default=50).int_value
    experiment_model_dict['globalBonus'] = experiment_configuration.get_parameter_value(
        name='group_cluster_bonus', default=50).int_value

# round configuration data
    experiment_model_dict['roundDuration'] = 10
    experiment_model_dict['networkStructure'] = 10
    practice_round = round_configuration.is_practice_round
    experiment_model_dict['practiceRound'] = practice_round
    experiment_model_dict['templateName'] = round_configuration.round_type
    if practice_round:
        experiment_model_dict[
            'templateName'] = RoundConfiguration.RoundType.REGULAR
    if practice_round and round_configuration.sequence_number == 3:
        experiment_model_dict['isFirstPracticeRound'] = True
        experiment_model_dict['isSecondPracticeRound'] = False
    elif practice_round and round_configuration.sequence_number == 4:
        experiment_model_dict['isFirstPracticeRound'] = False
        experiment_model_dict['isSecondPracticeRound'] = True
    else:
        experiment_model_dict['isFirstPracticeRound'] = False
        experiment_model_dict['isSecondPracticeRound'] = False

    #experiment_model_dict['networkStructureImageBackgroundUrl'] = "{{ STATIC_URL }}images/broker/SES.jpg"

# round data
# group data values
# FIXME: make sure round_setup initializes these GroupRoundDataValues properly by looking them up from the
# RoundConfiguration and assigning them
    experiment_model_dict['localThreshold'] = group.get_data_value(
        parameter_name='group_local_bonus_threshold', round_data=round_data, default=5).int_value
    experiment_model_dict['globalThreshold'] = group.get_data_value(
        parameter_name='group_cluster_bonus_threshold', round_data=round_data, default=22).int_value

    # data from the last round
    experiment_model_dict['lastRoundHarvestDecision'] = get_harvest_decision(
        participant_group_relationship, round_data=previous_round_data)
    experiment_model_dict['lastRoundConservationDecision'] = get_conservation_decision(
        participant_group_relationship, round_data=previous_round_data)
    experiment_model_dict['lastRoundMyGroupConservation'] = 10
    experiment_model_dict['lastRoundGlobalConservation'] = 10
    experiment_model_dict['lastRoundGroupLocalBonus'] = 10
    experiment_model_dict['lastRoundGroupGlobalBonus'] = 10
    experiment_model_dict['lastRoundHarvestPayOff'] = get_payoff(
        participant_group_relationship, round_data=previous_round_data)
    experiment_model_dict['totalEarning'] = 100
    number_of_connected_groups = round_configuration.get_parameter_value(
        name='number_of_connected_groups', default=2).int_value
    experiment_model_dict['participantsPerSubGroup'] = group.max_size
    experiment_model_dict[
        'participantsPerGroup'] = group.max_size * number_of_connected_groups

    experiment_model_dict.update(**kwargs)
    return dumps(experiment_model_dict)
