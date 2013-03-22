from django.shortcuts import get_object_or_404, render, redirect
from vcweb.core.models import Experiment, ParticipantGroupRelationship
from vcweb.core.decorators import participant_required
from vcweb.core import dumps
from vcweb.core.forms import ParticipantGroupIdForm, SingleIntegerDecisionForm
from vcweb.core.http import JsonResponse
from vcweb.core.models import (is_participant, is_experimenter, Experiment, ParticipantGroupRelationship,
        ParticipantExperimentRelationship, RoundConfiguration, ChatMessage, ParticipantRoundDataValue)

from vcweb.broker.models import (get_max_harvest_hours, get_harvest_decision_parameter,
        get_conservation_decision_parameter, set_harvest_decision, set_conservation_decision)

import random

import logging

logger = logging.getLogger(__name__)

@participant_required
def submit_decision(request, experiment_id=None):
    form = SingleIntegerDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        logger.debug("handing POST request, cleaned data: %s", form.cleaned_data)
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        harvest_hours = form.cleaned_data['integer_decision']
        conservation_hours = get_max_harvest_hours(experiment) - harvest_hours
        round_data = experiment.current_round_data
        set_harvest_decision(pgr, harvest_hours, round_data=round_data)
        set_conservation_decision(pgr, conservation_hours, round_data=round_data)
        return JsonResponse(dumps({ 'success': True, 'experimentModelJson': get_view_model_json(experiment, pgr)}))
    for field in form:
        if field.errors:
            logger.debug("field %s had errors %s", field, field.errors)
    return JsonResponse(dumps({'success': False }))

@participant_required
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

@participant_required
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=request.GET.get('participant_group_id'))
    return JsonResponse(get_view_model_json(experiment, participant_group_relationship))

def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    experiment_model_dict = experiment.to_dict(include_round_data=False)
    group = participant_group_relationship.group
    experiment_configuration = experiment.experiment_configuration
    round_configuration = experiment.current_round
    round_data = experiment.current_round_data

# experiment configuration data
    experiment_model_dict['maxHarvestDecision'] = 10
    experiment_model_dict['maxEarnings'] = 20.00
    experiment_model_dict['localBonus'] = experiment_configuration.get_parameter_value(name='group_local_bonus', default=50).int_value
    experiment_model_dict['globalBonus'] = experiment_configuration.get_parameter_value(name='group_cluster_bonus', default=50).int_value

# round configuration data
    experiment_model_dict['chatEnabled'] = True
    experiment_model_dict['roundDuration'] = 10
    experiment_model_dict['networkStructure'] = 10
    practice_round = round_configuration.is_practice_round
    experiment_model_dict['practiceRound'] = practice_round
    experiment_model_dict['templateName'] = round_configuration.round_type
    if practice_round:
        experiment_model_dict['templateName'] = RoundConfiguration.RoundType.REGULAR
    if practice_round and round_configuration.sequence_number == 3:
        experiment_model_dict['isFirstPracticeRound'] = True
        experiment_model_dict['isSecondPracticeRound'] = False
    elif practice_round and round_configuration.sequence_number == 4:
        experiment_model_dict['isFirstPracticeRound'] = False
        experiment_model_dict['isSecondPracticeRound'] = True
    else:
        experiment_model_dict['isFirstPracticeRound'] = False
        experiment_model_dict['isSecondPracticeRound'] = False

    experiment_model_dict['networkStructureImageBackgroundUrl'] = "{{ STATIC_URL }}images/broker/SES.jpg"

# round data
# group data values
# FIXME: make sure round_setup initializes these GroupRoundDataValues properly by looking them up from the
# RoundConfiguration and assigning them
    experiment_model_dict['localThreshold'] = group.get_data_value(parameter_name='group_local_bonus_threshold', round_data=round_data, default=5).int_value
    experiment_model_dict['globalThreshold'] = group.get_data_value(parameter_name='group_cluster_bonus_threshold', round_data=round_data, default=22).int_value

    # data from the last round
    experiment_model_dict['lastRoundHarvestDecision'] = 5
    experiment_model_dict['lastRoundMyGroupConservation'] = 10
    experiment_model_dict['lastRoundGlobalConservation'] = 10
    experiment_model_dict['lastRoundGroupLocalBonus'] = 10
    experiment_model_dict['lastRoundGroupGlobalBonus'] = 10
    experiment_model_dict['lastRoundHarvestPayOff'] = 5
    experiment_model_dict['totalEarning'] = 100
    number_of_connected_groups = round_configuration.get_parameter_value(name='number_of_connected_groups', default=2).int_value
    experiment_model_dict['participantsPerSubGroup'] = group.max_size
    experiment_model_dict['participantsPerGroup'] = group.max_size * number_of_connected_groups





    experiment_model_dict.update(**kwargs)
    return dumps(experiment_model_dict)
