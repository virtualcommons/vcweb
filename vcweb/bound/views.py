from collections import Counter
from operator import itemgetter
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from vcweb.core import dumps
from vcweb.core.decorators import participant_required
from vcweb.core.http import JsonResponse
from vcweb.core.models import (Experiment, ParticipantGroupRelationship, ChatMessage, GroupRelationship)
from vcweb.bound.forms import SingleIntegerDecisionForm
from vcweb.bound.models import (get_experiment_metadata, get_regrowth_rate, get_max_allowed_harvest_decision,
        get_cost_of_living, get_resource_level, get_initial_resource_level, get_total_storage, get_storage,
        get_all_session_storages, get_last_harvest_decision, get_harvest_decision_dv, get_harvest_decision_parameter,
        set_harvest_decision, can_observe_other_group, get_average_harvest, get_average_storage,
        get_total_harvest, get_number_alive, get_player_data)

from urllib import urlencode
import logging
logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)
    if experiment.experiment_metadata != get_experiment_metadata() or pgr.participant != request.user.participant:
        raise Http404
    return render(request, experiment.participant_template, {
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
        submitted = form.cleaned_data['submitted']
        logger.debug("pgr %s harvested %s - final submission? %s", pgr, harvest_decision, submitted)
        round_data = experiment.current_round_data
        set_harvest_decision(pgr, harvest_decision, round_data, submitted=submitted)
        message = "%s harvested %s trees"
        experiment.log(message % (pgr.participant, harvest_decision))
        response_dict = {
                'success': True,
#                'experimentModelJson': get_view_model_json(experiment, pgr),
                'message': message % (pgr.participant_handle, harvest_decision),
                }
        return JsonResponse(dumps(response_dict))
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
    return JsonResponse(get_view_model_json(experiment, pgr))

experiment_model_defaults = {
        'submitted': False,
        'chatEnabled': False,
        'resourceLevel': 0,
        'maxEarnings': 20.00,
        'maximumResourcesToDisplay': 20,
        'warningCountdownTime': 10,
        'harvestDecision': 0,
        'storage': 0,
        'roundDuration': 60,
        'chatMessages': [],
        'canObserveOtherGroup': False,
        'selectedHarvestDecision': False,
        'isInstructionsRound': False,
        'waitThirtySeconds': False,
        'totalHarvest': 0,
        'sessionOneStorage': 0,
        'sessionTwoStorage': 0,
        'numberAlive': '4 out of 4',
        'surveyUrl': 'http://survey.qualtrics.com/SE/?SID=SV_0vzmIj5UsOgjoTX',
        }
# FIXME: bloated method with too many special cases, try to refactor
def get_view_model_json(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    previous_round = experiment.previous_round
    previous_round_data = experiment.get_round_data(round_configuration=previous_round)
    experiment_model_dict = experiment.to_dict(include_round_data=False, default_value_dict=experiment_model_defaults)
    logger.debug("returning view model json for round %s" % current_round)

# round / experiment configuration data
    experiment_model_dict['timeRemaining'] = experiment.time_remaining
    experiment_model_dict['sessionId'] = current_round.session_id
    regrowth_rate = get_regrowth_rate(current_round)
    cost_of_living = get_cost_of_living(current_round)
    experiment_model_dict['costOfLiving'] = cost_of_living
    experiment_model_dict['maxHarvestDecision'] = get_max_allowed_harvest_decision(participant_group_relationship, current_round_data, ec)
    experiment_model_dict['templateName'] = current_round.template_name
    experiment_model_dict['isPracticeRound'] = current_round.is_practice_round
    # FIXME: only show the tour on the first practice round.. this is a bit brittle, maybe simply tie it to round #2?
    experiment_model_dict['showTour'] = current_round.is_practice_round and not previous_round.is_practice_round
# instructions round parameters
    if current_round.is_instructions_round:
        experiment_model_dict['isInstructionsRound'] = True
        experiment_model_dict['participantsPerGroup'] = ec.max_group_size
        experiment_model_dict['regrowthRate'] = regrowth_rate
        experiment_model_dict['initialResourceLevel'] = get_initial_resource_level(current_round)
    if current_round.is_regular_round:
        experiment_model_dict['chatEnabled'] = current_round.chat_enabled

    if current_round.is_debriefing_round:
        experiment_model_dict['totalHarvest'] = get_total_harvest(participant_group_relationship, current_round.session_id)
        if experiment.is_last_round:
            (session_one_storage, session_two_storage) = get_all_session_storages(experiment, participant_group_relationship)
            experiment_model_dict['sessionOneStorage'] = session_one_storage
            experiment_model_dict['sessonTwoStorage'] = session_two_storage

    if current_round.is_survey_enabled:
        logger.debug("survey was enabled")
        query_parameters = urlencode({
            'pid': participant_group_relationship.pk,
            'eid': experiment.pk,
            'tid': experiment.experiment_configuration.treatment_id,
            })
        survey_url = current_round.survey_url
        separator = '?'
        if separator in survey_url:
            separator = '&'
        experiment_model_dict['surveyUrl'] = "{0}{1}{2}".format(current_round.survey_url, separator, query_parameters)


# participant data
    experiment_model_dict['participantNumber'] = participant_group_relationship.participant_number
    experiment_model_dict['participantGroupId'] = participant_group_relationship.pk
    # FIXME: these should only need to be added for playable rounds but KO gets unhappy when we switch templates from
    # instructions rounds to practice rounds.
    own_group = participant_group_relationship.group
    own_resource_level = get_resource_level(own_group)
    if current_round.is_playable_round or current_round.is_debriefing_round:
        player_data, own_data = get_player_data(own_group, previous_round_data, current_round_data, participant_group_relationship)
        logger.debug("player data: %s", player_data)
        experiment_model_dict.update(own_data)
        experiment_model_dict['playerData'] = player_data
        experiment_model_dict['averageHarvest'] = get_average_harvest(own_group, previous_round_data)
        experiment_model_dict['averageStorage'] = get_average_storage(own_group, current_round_data)
        c = Counter(map(itemgetter('alive'), experiment_model_dict['playerData']))
        experiment_model_dict['numberAlive'] = "%s out of %s" % (c[True], sum(c.values()))
        logger.debug("playable round, number alive is: %s", experiment_model_dict['numberAlive'])
    experiment_model_dict['resourceLevel'] = own_resource_level
    # participant group data parameters are only needed if this round is a data round or the previous round was a data round
    if previous_round.is_playable_round or current_round.is_playable_round:
        harvest_decision = get_harvest_decision_dv(participant_group_relationship, current_round_data)
        experiment_model_dict['submitted'] = harvest_decision.submitted
        if harvest_decision.submitted:
            # user has already submit a harvest decision this round
            experiment_model_dict['harvestDecision'] = harvest_decision.int_value
            logger.debug("already submitted, setting harvest decision to %s", experiment_model_dict['harvestDecision'])

        experiment_model_dict['chatMessages'] = [cm.to_dict() for cm in ChatMessage.objects.for_group(own_group)]
        if can_observe_other_group(current_round):
            experiment_model_dict['canObserveOtherGroup'] = True
            other_group = own_group.get_related_group()
            experiment_model_dict['otherGroupResourceLevel'] = get_resource_level(other_group, current_round_data)
            experiment_model_dict['otherGroupAverageHarvest'] = get_average_harvest(other_group, previous_round_data)
            experiment_model_dict['otherGroupAverageStorage'] = get_average_storage(other_group, current_round_data)
            number_alive = get_number_alive(other_group, current_round_data)
            experiment_model_dict['otherGroupNumberAlive'] = "%s out of %s" % (number_alive, other_group.size)

    return dumps(experiment_model_dict)
