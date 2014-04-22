from django.db import models, transaction
from collections import defaultdict
from django.dispatch import receiver
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue, DefaultValue,
                               RoundConfiguration)
from vcweb.core import signals, simplecache
import logging

logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = intern('forestry')
MAX_RESOURCE_LEVEL = 100


def get_resource_level_dv(group, round_data=None, default=MAX_RESOURCE_LEVEL):
    return group.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data, default=default)


def get_resource_level(group, round_data=None, **kwargs):
    """ returns the group resource level data value scalar """
    return get_resource_level_dv(group, round_data=round_data, **kwargs).int_value


def get_group_harvest_dv(group, round_data=None):
    """ returns the collective group harvest data value """
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data)


def get_group_harvest(group, round_data=None):
    """ returns the collective group harvest data value """
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data).int_value


def get_regrowth_dv(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0)


# returns the number of resources regenerated for the given group in the given round
def get_regrowth(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0).int_value


def get_regrowth_rate(current_round, default=0.1):
    return current_round.get_parameter_value(get_regrowth_rate_parameter(), default=default).float_value


def has_resource_level(group=None):
    return group.has_data_parameter(parameter=get_resource_level_parameter())


def get_harvest_decision_dv(participant_group_relationship, round_data=None, default=0):
    return participant_group_relationship.get_data_value(round_data=round_data,
                                                         parameter=get_harvest_decision_parameter(), default=default)


def get_harvest_decision(participant_group_relationship, round_data=None, default=0):
    return get_harvest_decision_dv(participant_group_relationship, round_data, default).int_value


def get_harvest_decisions(group=None):
    return group.get_participant_data_values(parameter__name='harvest_decision') if group else []


def set_regrowth(group, value, round_data=None):
    group.set_data_value(parameter=get_regrowth_parameter(), value=value, round_data=round_data)


def set_group_harvest(group, value, round_data=None):
    group.set_data_value(parameter=get_group_harvest_parameter(), value=value, round_data=round_data)


# FIXME: Boundry Effects Experiment also uses this and has a duplicate version in bound/models.py
def should_reset_resource_level(round_configuration, experiment):
    if round_configuration.is_repeating_round and experiment.current_repeated_round_sequence_number > 0:
        return False
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(),
                                                   default=False).boolean_value


def get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL):
    return round_configuration.get_parameter_value(parameter=get_initial_resource_level_parameter(),
                                                   default=default).int_value


def get_max_harvest_decision(resource_level):
    if resource_level >= 25:
        return 5
    elif resource_level >= 20:
        return 4
    elif resource_level >= 15:
        return 3
    elif resource_level >= 10:
        return 2
    elif resource_level >= 5:
        return 1
    else:
        return 0


def get_average_harvest(group, round_data):
    return get_total_group_harvest(group, round_data) / float(group.size)


def get_max_resource_level(round_configuration):
    return get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL)


# def is_shared_resource_enabled(round_configuration):
#     return round_configuration.get_parameter_value(parameter=get_shared_resource_enabled_parameter(),
#                                                    default=False).boolean_value


def get_max_allowed_harvest_decision(participant_group_relationship, round_data=None, experiment_configuration=None):
    return get_max_harvest_decision(experiment_configuration)


def _zero_if_none(value):
    return 0 if value is None else value


def get_total_experiment_harvest(experiment, pgr, practice=False):

    if practice:
        debriefing_session_round_data = experiment.round_data_set.filter(
            round_configuration__round_type=RoundConfiguration.RoundType.PRACTICE)
    else:
        debriefing_session_round_data = experiment.round_data_set.filter(
            round_configuration__round_type=RoundConfiguration.RoundType.REGULAR)

    q = ParticipantRoundDataValue.objects.for_participant(participant_group_relationship=pgr,
                                                          parameter=get_harvest_decision_parameter(),
                                                          round_data__in=debriefing_session_round_data)\
        .aggregate(total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


def get_total_group_harvest(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(group=group, parameter=get_harvest_decision_parameter(),
                                                    round_data=round_data) \
        .aggregate(total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


# def get_total_harvest(participant_group_relationship, session_id):
#     q = ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
#                                                           parameter=get_harvest_decision_parameter(),
#                                                           participant_group_relationship__group__session_id=session_id) \
#         .aggregate(total_harvest=models.Sum('int_value'))
#     return _zero_if_none(q['total_harvest'])


def get_player_data(previous_round_data, current_round_data, self_pgr):
    """ Returns a tuple ([list of player data dictionaries], { dictionary of this player's data })"""
    # FIXME: refactor this into its own class as opposed to an arcane data structure
    prdvs = ParticipantRoundDataValue.objects.for_group(group=self_pgr.group,
                                                        parameter=get_harvest_decision_parameter(),
                                                        round_data__in=[previous_round_data, current_round_data])
    # nested dict mapping participant group relationship -> dict(parameter -> participant round data value)
    logger.debug(prdvs)
    if prdvs:
        player_dict = defaultdict(lambda: defaultdict(lambda: None))

        for prdv in prdvs:
            player_dict[prdv.participant_group_relationship][prdv.parameter] = prdv

        player_data = []

        for pgr, pgrdv_dict in player_dict.iteritems():
            # FIXME: figure out a way to handle default values elegantly in this case since we aren't using the accessor
            # methods
            for int_parameter in (get_harvest_decision_parameter(), get_storage_parameter()):
                if pgrdv_dict[int_parameter] is None:
                    pgrdv_dict[int_parameter] = DefaultValue(0)

            logger.debug(pgr.pk)
            player_data.append({
                'id': pgr.pk,
                'number': pgr.participant_number,
                'lastHarvestDecision': pgrdv_dict[get_harvest_decision_parameter()].int_value
            })
        own_player = player_dict[self_pgr]

        if own_player[get_harvest_decision_parameter()]:
            return (player_data, {
                'lastHarvestDecision': own_player[get_harvest_decision_parameter()].int_value
            })
        else:
            return (player_data, {
                'lastHarvestDecision': 0
            })

    return (
        [], {'lastHarvestDecision': 0}
    )


def set_harvest_decision(participant_group_relationship=None, value=None, round_data=None, submitted=False):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    # deactivate all previous harvest decisions in this round
    ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
                                                      parameter=get_harvest_decision_parameter(),
                                                      round_data=round_data).update(is_active=False)
    return ParticipantRoundDataValue.objects.create(participant_group_relationship=participant_group_relationship,
                                                    parameter=get_harvest_decision_parameter(), round_data=round_data,
                                                    int_value=value,
                                                    submitted=submitted)


# def set_resource_level(group, value, round_data=None):
#     return group.set_data_value(parameter=get_resource_level_parameter(), round_data=round_data, value=value)


@simplecache
def get_storage_parameter():
    return Parameter.objects.for_participant(name='storage')


@simplecache
def get_cost_of_living_parameter():
    return Parameter.objects.for_round(name='cost_of_living')


@simplecache
def get_shared_resource_enabled_parameter():
    return Parameter.objects.for_round(name='shared_resource')


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace=EXPERIMENT_METADATA_NAME)


@simplecache
def get_resource_level_parameter():
    return Parameter.objects.for_group(name='resource_level')


@simplecache
def get_regrowth_rate_parameter():
    return Parameter.objects.for_round(name='regrowth_rate')


# parameter for the amount of resources that were regrown at the end of the given round for the given group
@simplecache
def get_regrowth_parameter():
    return Parameter.objects.for_group(name='group_regrowth')


@simplecache
def get_group_harvest_parameter():
    return Parameter.objects.for_group(name='group_harvest')


@simplecache
def get_harvest_decision_parameter():
    return Parameter.objects.for_participant(name='harvest_decision')


@simplecache
def get_reset_resource_level_parameter():
    return Parameter.objects.for_round(name='reset_resource_level')


@simplecache
def get_initial_resource_level_parameter():
    return Parameter.objects.for_round(name='initial_resource_level')


@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_started_handler(sender, experiment=None, **kwargs):
    if experiment is None:
        logger.error("Received round started signal with no experiment: %s", sender)
        raise ValueError("Received round started signal with no experiment")

    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("setting up round %s", round_configuration)

    # initialize group, group cluster, and participant data values
    experiment.initialize_data_values(
        group_parameters=(get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter()),
        defaults={get_regrowth_parameter(): 0}
    )

    if should_reset_resource_level(round_configuration, experiment):
        initial_resource_level = get_max_resource_level(round_configuration)
        logger.debug("Resetting resource level for all groups in %s to %d", round_configuration, initial_resource_level)

        for group in experiment.groups:
            # set resource level to initial default
            existing_resource_level = get_resource_level_dv(group, round_data, round_configuration)
            group.log("Resetting resource level (%s) to initial value [%s]" %
                      (existing_resource_level, initial_resource_level))
            existing_resource_level.update_int(initial_resource_level)


@transaction.atomic
def update_resource_level(experiment, group, round_data, regrowth_rate, max_resource_level=None):
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(round_data.round_configuration)

    current_resource_level_dv = get_resource_level_dv(group, round_data)
    current_resource_level = current_resource_level_dv.int_value
    group_harvest_dv = get_group_harvest_dv(group, round_data)

    logger.debug("The group harvest is %s", group_harvest_dv)
    regrowth_dv = get_regrowth_dv(group, round_data)

    total_harvest = get_total_group_harvest(group, round_data)
    logger.debug("Harvest: total group harvest for playable round: %s", total_harvest)

    if current_resource_level > 0 and total_harvest > 0:
        group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
        group_harvest_dv.update_int(total_harvest)
        current_resource_level = current_resource_level - total_harvest
        resource_regrowth = calculate_regrowth(current_resource_level, regrowth_rate, max_resource_level)
        group.log("Regrowth: adding %s to current resource level %s" % (resource_regrowth, current_resource_level))
        regrowth_dv.update_int(resource_regrowth)
        # clamp resource
        current_resource_level_dv.update_int(min(current_resource_level + resource_regrowth, max_resource_level))
    ''' XXX: transfer resource levels across chat and quiz rounds if they exist '''
    if experiment.has_next_round:
        ''' set group round data resource_level for each group + regrowth '''
        group.log("Transferring resource level %s to next round" % current_resource_level_dv.int_value)
        logger.debug("The regrowth_dv is: %s or %s", regrowth_dv.int_value, regrowth_dv.value)
        group.copy_to_next_round(current_resource_level_dv, group_harvest_dv, regrowth_dv)


@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_ended_handler(sender, experiment=None, **kwargs):
    """
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    """
    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("ending forestry round: %s", round_configuration)

    if round_configuration.is_playable_round:
        regrowth_rate = get_regrowth_rate(round_configuration)
        harvest_decision_parameter = get_harvest_decision_parameter()
        # zero out not submitted harvest decisions
        for pgr in experiment.participant_group_relationships:
            prdvs = ParticipantRoundDataValue.objects.filter(
                round_data=round_data,
                participant_group_relationship=pgr,
                parameter=harvest_decision_parameter,
                is_active=True)
            if prdvs.count() == 0:
                prdv = ParticipantRoundDataValue.objects.create(
                    round_data=round_data,
                    participant_group_relationship=pgr,
                    parameter=harvest_decision_parameter,
                    is_active=True,
                    int_value=0)
                logger.debug("created new harvest decision prdv %s for participant %s", prdv, pgr)

        for group in experiment.groups:
            logger.debug("group %s has resource level", group)
            update_resource_level(experiment, group, round_data, regrowth_rate)


def calculate_regrowth(resource_level, regrowth_rate, max_resource_level):
    if resource_level == max_resource_level:
        return 0
    logger.debug("calculating regrowth: (%s * %s) * (1 - (%s / %s))", regrowth_rate, resource_level, resource_level,
                 max_resource_level)
    return regrowth_rate * resource_level