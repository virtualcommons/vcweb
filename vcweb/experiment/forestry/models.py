import logging
import sys
from collections import defaultdict

from django.db import models, transaction
from django.dispatch import receiver

from vcweb.core import signals, simplecache
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue, RoundConfiguration, )

logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = sys.intern('forestry')
MAX_RESOURCE_LEVEL = 100


def get_resource_level_dv(group, round_data=None, default=MAX_RESOURCE_LEVEL):
    return group.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data, default=default)


def get_resource_level(group, round_data=None, **kwargs):
    """ return the group resource level data value scalar """
    return get_resource_level_dv(group, round_data=round_data, **kwargs).int_value


def get_group_harvest_dv(group, round_data=None):
    """
    return the collective group harvest (total number of resources harvested by all members in the group) as a
    DataValue
    """
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data)


def get_group_harvest(group, round_data=None):
    """
    return the collective group harvest (total number of resources harvested by all members in the group) as an
    integer
    """
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data).int_value


def get_regrowth_dv(group, round_data=None):
    """
    return the number of resources regenerated for the given group in the given round as a DataValue
    """
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0)


def get_regrowth(group, round_data=None):
    """
    return the number of resources regenerated for the given group in the given round as an integer
    """
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


def set_regrowth(group, value, round_data=None):
    group.set_data_value(
        parameter=get_regrowth_parameter(), value=value, round_data=round_data)


def set_group_harvest(group, value, round_data=None):
    group.set_data_value(
        parameter=get_group_harvest_parameter(), value=value, round_data=round_data)


def can_view_group_results(round_configuration, default=True):
    return round_configuration.get_parameter_value(name='view_group_results', default=default, inheritable=True)


# FIXME: duplicate version in Boundary Effects bound/models.py, see if we can refactor
def should_reset_resource_level(round_configuration, experiment):
    if round_configuration.is_repeating_round and experiment.current_repeated_round_sequence_number > 0:
        return False
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(),
                                                   default=False).boolean_value


def get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL):
    return round_configuration.get_parameter_value(parameter=get_initial_resource_level_parameter(),
                                                   default=default).int_value


def get_average_harvest(group, round_data):
    return get_total_group_harvest(group, round_data) / float(group.size)


def get_max_resource_level(round_configuration):
    return get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL)


# def is_shared_resource_enabled(round_configuration):
#     return round_configuration.get_parameter_value(parameter=get_shared_resource_enabled_parameter(),
#                                                    default=False).boolean_value


def _default_max_harvest_decision(resource_level):
    # FIXME: figure out a flexible way to manage different max harvest functions
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


def _daniel_decaro_max_harvest_function(resource_level):
    if resource_level >= 40:
        return 10
    elif resource_level >= 32:
        return 8
    elif resource_level >= 24:
        return 6
    elif resource_level >= 16:
        return 4
    elif resource_level >= 8:
        return 2
    else:
        return 0


def _max_harvest_decision_function(treatment_id, resource_level):
    # FIXME: horrible hackiness, figure out how to embed different max harvest functions for different treatments
    # https://github.com/virtualcommons/vcweb/issues/105
    if 'daniel.decaro' in treatment_id:
        return _daniel_decaro_max_harvest_function(resource_level)
    return _default_max_harvest_decision(resource_level)


def get_max_harvest_decision(group, round_data=None, experiment_configuration=None):
    resource_level = get_resource_level(group, round_data)
    if experiment_configuration is None:
        return _default_max_harvest_decision(resource_level)
    treatment_id = experiment_configuration.treatment_id
    return _max_harvest_decision_function(treatment_id, resource_level)


def _zero_if_none(value):
    return 0 if value is None else value


def get_total_experiment_harvest(pgr, debriefing_session_round_data):
    q = ParticipantRoundDataValue.objects.for_participant(
        participant_group_relationship=pgr,
        parameter=get_harvest_decision_parameter(),
        round_data__in=debriefing_session_round_data
    ).aggregate(total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


def get_total_group_harvest(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(
        group=group, parameter=get_harvest_decision_parameter(), round_data=round_data
    ).aggregate(total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


class GroupData(object):

    def __init__(self, self_pgr, previous_round_data, current_round_data):
        self.pgr = self_pgr
        self.group = self_pgr.group
        self.player_dict = defaultdict(lambda: defaultdict(lambda: None))
        self.exchange_rate = current_round_data.round_configuration.experiment_configuration.exchange_rate

        prdvs = ParticipantRoundDataValue.objects.for_group(
            group=self.group,
            parameter=get_harvest_decision_parameter(),
            round_data=previous_round_data)

        # Converting django ORM object to dictionary to retrieve data by parameter
        for prdv in prdvs:
            self.player_dict[prdv.participant_group_relationship][prdv.parameter] = prdv
        self.group_data = []
# include practice rounds totals in harvest if this current round is a practice round
        include_practice_rounds = current_round_data.round_configuration.is_practice_round
        for pgr in self.group.participant_group_relationship_set.all():
            # subtract current harvest from the total harvest so other participants won't get extra information
            current_harvest = get_harvest_decision(pgr, current_round_data)
            total_harvest = max(0, self.total_harvest(pgr, include_practice_rounds) - current_harvest)
            logger.debug("total harvest: %s after subtracting current harvest %s", total_harvest, current_harvest)
            self.group_data.append({
                'id': pgr.pk,
                'number': pgr.participant_number,
                'lastHarvestDecision': self.get_last_harvest_decision(pgr),
                'totalHarvest': total_harvest,
                'totalEarnings': total_harvest * self.exchange_rate
            })

    def get_last_harvest_decision(self, pgr):
        try:
            return self.player_dict[pgr][get_harvest_decision_parameter()].int_value
        except:
            return 0

    def total_harvest(self, pgr, include_practice_rounds=False):
        q = ParticipantRoundDataValue.objects.for_participant(
            participant_group_relationship=pgr,
            parameter=get_harvest_decision_parameter()
        )
        if not include_practice_rounds:
            q = q.exclude(round_data__round_configuration__round_type=RoundConfiguration.RoundType.PRACTICE)
        q = q.aggregate(total=models.Sum('int_value'))
        return _zero_if_none(q['total'])

    def get_group_data(self):
        return self.group_data

    def get_total_harvest(self, pgr):
        for player_data in self.group_data:
            if player_data['id'] == pgr.pk:
                return player_data['totalHarvest']
        logger.warning("No total harvest found for pgr %s", pgr)
        return 0

    def get_own_data(self):
        for player_data in self.group_data:
            if player_data['id'] == self.pgr.pk:
                return player_data

    def get_group_earnings(self, round_list, exchange_rate):
        group_data = []
        for pgr in self.group.participant_group_relationship_set.all():
            if pgr != self.pgr:
                group_data.append({
                    'number': pgr.participant_number,
                    'totalEarnings': get_total_experiment_harvest(pgr, round_list) * exchange_rate
                })
        return group_data

    def get_own_earnings(self, round_list, exchange_rate):
        return get_total_experiment_harvest(self.pgr, round_list) * exchange_rate


@transaction.atomic
def set_harvest_decision(participant_group_relationship=None, value=None, round_data=None, submitted=False):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    # deactivate all previous harvest decisions in this round
    ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
                                                      parameter=get_harvest_decision_parameter(),
                                                      round_data=round_data).update(is_active=False)
    prdv = ParticipantRoundDataValue.objects.create(participant_group_relationship=participant_group_relationship,
                                                    parameter=get_harvest_decision_parameter(), round_data=round_data,
                                                    int_value=value,
                                                    submitted=submitted)
    return prdv


def set_resource_level(group, value, round_data=None):
    return group.set_data_value(parameter=get_resource_level_parameter(), round_data=round_data, value=value)


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


# parameter for the amount of resources that were regrown at the end of
# the given round for the given group
@simplecache
def get_regrowth_parameter():
    return Parameter.objects.for_group(name='regrowth')


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


# FIXME: consider refactoring, move signal receivers to signals.py and
# dependent functions to services.py

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
        defaults={
            get_regrowth_parameter(): 0
        }
    )

    if should_reset_resource_level(round_configuration, experiment):
        initial_resource_level = get_max_resource_level(round_configuration)
        logger.debug("Resetting resource level for all groups in %s to %d",
                     round_configuration, initial_resource_level)
        for group in experiment.groups:
            # set resource level to initial default values
            existing_resource_level = get_resource_level_dv(group, round_data)
            group.log("Resetting resource level (%s) to initial value [%s]" % (
                existing_resource_level, initial_resource_level))
            existing_resource_level.update_int(initial_resource_level)


@transaction.atomic
def update_resource_level(experiment, group, round_data, regrowth_rate, max_resource_level=None):
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(round_data.round_configuration)
    current_resource_level_dv = get_resource_level_dv(group, round_data)
    current_resource_level = current_resource_level_dv.int_value
    group_harvest_dv = get_group_harvest_dv(group, round_data)
    regrowth_dv = get_regrowth_dv(group, round_data)
    total_harvest = get_total_group_harvest(group, round_data)
    logger.debug("Harvest: total group harvest for playable round: %s", total_harvest)
    if current_resource_level > 0:
        group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
        group_harvest_dv.update_int(total_harvest)
        current_resource_level = current_resource_level - total_harvest
        resource_regrowth = calculate_regrowth(current_resource_level, regrowth_rate, max_resource_level)
        group.log("Regrowth: adding %s to current resource level %s" %
                  (resource_regrowth, current_resource_level))
        regrowth_dv.update_int(resource_regrowth)
        # clamp resource
        current_resource_level_dv.update_int(min(current_resource_level + resource_regrowth, max_resource_level))
    # XXX: transfer resource levels across chat and quiz rounds if they exist
    if experiment.has_next_round:
        # set group round data resource_level for each group + regrowth
        group.log("Transferring resource level %s to next round" %
                  current_resource_level_dv.int_value)
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
                round_data=round_data, participant_group_relationship=pgr,
                parameter=harvest_decision_parameter, is_active=True
            )
            # If no harvest decision was submitted by the participant then
            # create one with default value
            if prdvs.count() == 0:
                prdv = ParticipantRoundDataValue.objects.create(
                    round_data=round_data, participant_group_relationship=pgr,
                    parameter=harvest_decision_parameter, is_active=True, int_value=0
                )
                logger.debug("created new harvest decision prdv %s for participant %s", prdv, pgr)
            elif prdvs.count() > 1:
                # multiple active harvest decisions, only allow the latest one
                # to be active
                latest_prdv = prdvs.latest('date_created')
                prdvs.exclude(pk=latest_prdv.pk).update(is_active=False)

        for group in experiment.groups:
            logger.debug("group %s has resource level", group)
            update_resource_level(experiment, group, round_data, regrowth_rate)


def calculate_regrowth(resource_level, regrowth_rate, max_resource_level):
    if resource_level == max_resource_level:
        return 0
    regrowth = regrowth_rate * resource_level
    logger.debug("calculated regrowth: %s * %s = %s", regrowth_rate, resource_level, regrowth)
    return regrowth
