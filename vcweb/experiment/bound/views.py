import logging
from collections import Counter
from operator import itemgetter

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect

from vcweb.core.decorators import group_required
from vcweb.core.forms import SingleIntegerDecisionForm
from vcweb.core.http import JsonResponse, dumps
from vcweb.core.models import (Experiment, ParticipantGroupRelationship, ChatMessage, PermissionGroup)
from vcweb.experiment.forestry.models import (set_harvest_decision, get_harvest_decision_dv, get_regrowth_dv)
from .models import (get_experiment_metadata, get_regrowth_rate, get_max_harvest_decision, get_cost_of_living,
                     get_resource_level, get_initial_resource_level, get_final_session_storage_queryset,
                     can_observe_other_group, get_average_harvest, get_average_storage, get_total_harvest,
                     get_number_alive, get_player_data)

logger = logging.getLogger(__name__)


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata',
                                                                     'experiment_configuration'),
                                   pk=experiment_id,
                                   experiment_metadata=get_experiment_metadata())
    if experiment.is_active:
        pgr = experiment.get_participant_group_relationship(participant)
        return render(request, experiment.participant_template, {
            'experiment': experiment,
            'participant_group_relationship': pgr,
            'group': pgr.group,
            'experimentModelJson': dumps(get_view_model_dict(experiment, pgr)),
        })
    else:
        messages.info(request, '%s has not been activated yet. Please try again later.' % experiment)
        return redirect('core:dashboard')


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def submit_harvest_decision(request, experiment_id=None):
    form = SingleIntegerDecisionForm(request.POST or None)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        pgr = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        harvest_decision = form.cleaned_data['integer_decision']
        submitted = form.cleaned_data['submitted']
        logger.debug("pgr %s harvested %s - final submission? %s",
                     pgr, harvest_decision, submitted)
        with transaction.atomic():
            round_data = experiment.current_round_data
            set_harvest_decision(pgr, harvest_decision, round_data, submitted=submitted)
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
    pgr = experiment.get_participant_group_relationship(request.user.participant)
    return JsonResponse(get_view_model_dict(experiment, pgr))


experiment_model_defaults = {
    'submitted': False,
    'chatEnabled': False,
    'alive': True,
    'resourceLevel': 0,
    'maxEarnings': 20.00,
    'maximumResourcesToDisplay': 20,
    'warningCountdownTime': 10,
    'harvestDecision': 0,
    'storage': 0,
    'roundDuration': 60,
    'chatMessages': [],
    'canObserveOtherGroup': False,
    'myGroup': {
        'resourceLevel': 0,
        'regrowth': 0,
        'originalResourceLevel': 0,
        'averageHarvest': 0,
        'averageStorage': 0,
        'numberAlive': 0,
        'isResourceEmpty': 0,
    },
    'otherGroup': {
        'resourceLevel': 0,
        'regrowth': 0,
        'originalResourceLevel': 0,
        'averageHarvest': 0,
        'averageStorage': 0,
        'numberAlive': 0,
        'isResourceEmpty': 0,
    },
    'selectedHarvestDecision': False,
    'waitThirtySeconds': False,
    'totalHarvest': 0,
    'sessionOneStorage': 0,
    'sessionTwoStorage': 0,
    'lastHarvestDecision': 0,
    'playerData': [],
    'averageHarvest': 0,
    'averageStorage': 0,
    'numberAlive': '4 out of 4',
    'surveyCompleted': False,
    'regrowth': 0,
    'surveyUrl': 'http://survey.qualtrics.com/SE/?SID=SV_0vzmIj5UsOgjoTX',
}
# FIXME: bloated method with too many special cases, refactor

def get_view_model_dict(experiment, participant_group_relationship, **kwargs):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    current_round_data = experiment.current_round_data
    previous_round = experiment.previous_round
    previous_round_data = experiment.get_round_data(round_configuration=previous_round, previous_round=True)
    experiment_model_dict = experiment.to_dict(
        include_round_data=False, default_value_dict=experiment_model_defaults)

    # round / experiment configuration data
    experiment_model_dict['timeRemaining'] = experiment.time_remaining
    experiment_model_dict['sessionId'] = current_round.session_id
    regrowth_rate = get_regrowth_rate(current_round)
    cost_of_living = get_cost_of_living(current_round)
    experiment_model_dict['costOfLiving'] = cost_of_living
    experiment_model_dict['maxHarvestDecision'] = get_max_harvest_decision(ec)
    experiment_model_dict['templateName'] = current_round.template_name
    experiment_model_dict['isPracticeRound'] = current_round.is_practice_round
    # FIXME: only show the tour on the first practice round, this is brittle. better to have a dedicated boolean flag on
    # RoundConfiguration?
    experiment_model_dict['showTour'] = current_round.is_practice_round and not previous_round.is_practice_round
    # instructions round parameters
    experiment_model_dict['isInstructionsRound'] = current_round.is_instructions_round
    experiment_model_dict['chatEnabled'] = current_round.chat_enabled
    experiment_model_dict['isSurveyEnabled'] = current_round.is_survey_enabled

    if current_round.is_instructions_round:
        experiment_model_dict['participantsPerGroup'] = ec.max_group_size
        experiment_model_dict['regrowthRate'] = regrowth_rate
        experiment_model_dict['initialResourceLevel'] = get_initial_resource_level(current_round)

    if current_round.is_survey_enabled:
        survey_url = current_round.build_survey_url(pid=participant_group_relationship.pk,
                                                    eid=experiment.pk,
                                                    tid=experiment.experiment_configuration.treatment_id)
        experiment_model_dict['surveyUrl'] = survey_url
        experiment_model_dict['surveyCompleted'] = participant_group_relationship.survey_completed
        logger.debug("survey enabled, setting survey url to %s", survey_url)

    if current_round.is_debriefing_round:
        experiment_model_dict['totalHarvest'] = get_total_harvest(participant_group_relationship,
                                                                  current_round.session_id)
        if experiment.is_last_round:
            (session_one_storage, session_two_storage) = get_final_session_storage_queryset(
                experiment, participant_group_relationship.participant)
            experiment_model_dict['sessionOneStorage'] = session_one_storage.int_value
            experiment_model_dict['sessionTwoStorage'] = session_two_storage.int_value

    # participant data
    experiment_model_dict['participantNumber'] = participant_group_relationship.participant_number
    experiment_model_dict['participantGroupId'] = participant_group_relationship.pk
    # FIXME: these should only need to be added for playable rounds but KO gets unhappy when we switch templates from
    # instructions rounds to practice rounds.
    own_group = participant_group_relationship.group
    own_resource_level = get_resource_level(own_group)
    if current_round.is_playable_round or current_round.is_debriefing_round:
        player_data, own_data = get_player_data(own_group, previous_round_data, current_round_data,
                                                participant_group_relationship)
        experiment_model_dict.update(own_data)
        experiment_model_dict['playerData'] = player_data
        experiment_model_dict['averageHarvest'] = get_average_harvest(own_group, previous_round_data)
        experiment_model_dict['averageStorage'] = get_average_storage(own_group, current_round_data)
        regrowth = experiment_model_dict['regrowth'] = get_regrowth_dv(own_group, current_round_data).value
        c = Counter(list(map(itemgetter('alive'), experiment_model_dict['playerData'])))
        experiment_model_dict['numberAlive'] = "%s out of %s" % (c[True], sum(c.values()))
        # FIXME: refactor duplication between myGroup and otherGroup data loading
        experiment_model_dict['myGroup'] = {
            'resourceLevel': own_resource_level,
            'regrowth': regrowth,
            'originalResourceLevel': own_resource_level - regrowth,
            'averageHarvest': experiment_model_dict['averageHarvest'],
            'averageStorage': experiment_model_dict['averageStorage'],
            'numberAlive': experiment_model_dict['numberAlive'],
            'isResourceEmpty': own_resource_level == 0,
        }

    experiment_model_dict['resourceLevel'] = own_resource_level

    # participant group data parameters are only needed if this round is a
    # data round or the previous round was a data round
    if previous_round.is_playable_round or current_round.is_playable_round:
        harvest_decision = get_harvest_decision_dv(participant_group_relationship, current_round_data)
        experiment_model_dict['submitted'] = harvest_decision.submitted
        if harvest_decision.submitted:
            # user has already submit a harvest decision this round
            experiment_model_dict['harvestDecision'] = harvest_decision.int_value
            logger.debug("already submitted, setting harvest decision to %s",
                         experiment_model_dict['harvestDecision'])

        experiment_model_dict['chatMessages'] = [cm.to_dict() for cm in ChatMessage.objects.for_group(own_group)]
        if can_observe_other_group(current_round):
            experiment_model_dict['canObserveOtherGroup'] = True
            other_group = own_group.get_related_group()
            number_alive = get_number_alive(other_group, current_round_data)
            resource_level = get_resource_level(other_group, current_round_data)
            regrowth = get_regrowth_dv(other_group, current_round_data).value
            experiment_model_dict['otherGroup'] = {
                'regrowth': regrowth,
                'resourceLevel': resource_level,
                'originalResourceLevel': resource_level - regrowth,
                'averageHarvest': get_average_harvest(other_group, previous_round_data),
                'averageStorage': get_average_storage(other_group, current_round_data),
                'numberAlive': "%s out of %s" % (number_alive, other_group.size),
                'isResourceEmpty': resource_level == 0,
            }
    return experiment_model_dict
