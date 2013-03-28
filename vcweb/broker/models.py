from django.db import models
from django.dispatch import receiver
from vcweb.core import signals, simplecache
from vcweb.core.models import (Parameter, ParticipantRoundDataValue, GroupCluster)
from vcweb.forestry.models import get_harvest_decision_parameter, set_harvest_decision, get_harvest_decision

import logging
logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = 'broker'

def get_max_harvest_hours(experiment):
    return experiment.experiment_configuration.get_parameter_value(name='max_hours', default=10).int_value

''' participant parameters '''
@simplecache
def get_chat_between_group_parameter():
    return Parameter.objects.get(name="chat_between_group")

@simplecache
def get_chat_within_group_parameter():
    return Parameter.objects.get(name="chat_within_group")

@simplecache
def get_participant_link_parameter():
    return Parameter.objects.get(name='participant_link')

@simplecache
def get_participant_payoff_parameter():
    return Parameter.objects.get(name='payoff')

@simplecache
def get_conservation_decision_parameter():
    return Parameter.objects.get(name='conservation_decision')

@simplecache
def get_payoff_parameter():
    return Parameter.objects.get(name='payoff')

''' group round parameters '''
@simplecache
def get_group_local_bonus_parameter():
    return Parameter.objects.get(name='group_local_bonus')

@simplecache
def get_group_cluster_bonus_parameter():
    return Parameter.objects.get(name='group_cluster_bonus')

''' round configuration parameters '''
@simplecache
def get_group_cluster_bonus_threshold_parameter():
    return Parameter.objects.get(name='group_cluster_bonus_threshold')

@simplecache
def get_group_local_bonus_threshold_parameter():
    return Parameter.objects.get(name='group_local_bonus_threshold')

def get_conservation_decision(participant_group_relationship, round_data=None):
    return participant_group_relationship.get_data_value(parameter=get_conservation_decision_parameter(),
            round_data=round_data, default=0).int_value

def set_conservation_decision(participant_group_relationship, value, round_data=None):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    prdv = ParticipantRoundDataValue.objects.get(parameter=get_conservation_decision_parameter(),
            participant_group_relationship=participant_group_relationship,
            round_data=round_data)
    prdv.int_value = value
    prdv.save()

def get_payoff_dv(participant_group_relationship, round_data=None, default=0):
    return participant_group_relationship.get_data_value(round_data=round_data, parameter=get_payoff_parameter(), default=default)

def get_payoff(participant_group_relationship, round_data=None, default=0):
    return get_payoff_dv(participant_group_relationship, round_data, default).int_value

def get_group_local_bonus_threshold(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_group_local_bonus_parameter(), default=5).int_value

def get_group_cluster_bonus_threshold(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_group_cluster_bonus_parameter(), default=22).int_value

@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
def round_started_handler(sender, experiment=None, **kwargs):
    if experiment is None:
        logger.error("Received round started signal with no experiment: %s", sender)
        raise ValueError("Received round started signal with no experiment")
    round_configuration = experiment.current_round
    logger.debug("setting up round %s", round_configuration)
    # initialize group and participant data values
    if round_configuration.is_playable_round:
        experiment.initialize_data_values(
                group_cluster_parameters=(get_group_cluster_bonus_parameter(),),
                group_parameters=(get_group_local_bonus_parameter(),),
                participant_parameters=(get_harvest_decision_parameter(), get_conservation_decision_parameter(),
                    get_participant_link_parameter(), get_participant_payoff_parameter(),
                    get_chat_between_group_parameter(), get_chat_within_group_parameter(),
                    )
                )

def calculate_group_local_bonus(group_conservation_hours, local_threshold):
    if group_conservation_hours > local_threshold:
        return 1.5
    else:
        return 1

def calculate_group_cluster_bonus(group_conservation_hours, local_threshold):
    if group_conservation_hours > local_threshold:
        return 2
    else:
        return 1

@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    current_round_configuration = experiment.current_round
    logger.debug("ending broker round: %s", current_round_configuration)
    round_data = experiment.current_round_data
    group_local_bonus_dict = {}
    group_cluster_bonus_dict = {}
    participant_conservation_dict = {}
    if current_round_configuration.is_playable_round:
        local_threshold = get_group_local_bonus_threshold(current_round_configuration)
        group_cluster_threshold = get_group_cluster_bonus_threshold(current_round_configuration)
        for group_cluster in GroupCluster.objects.for_experiment(experiment):
            group_cluster_conservation_hours = 0
            for group_relationship in group_cluster.group_relationship_set.all():
                group_conservation_hours = 0
                group = group_relationship.group
                for pgr in group.participant_group_relationship_set.all():
                    conservation_hours = get_conservation_decision(pgr, round_data=round_data)
                    participant_conservation_dict[pgr] = conservation_hours
                    group_conservation_hours += conservation_hours
                local_bonus = calculate_group_local_bonus(group_conservation_hours, local_threshold)
                group_local_bonus_dict[group] = local_bonus
                group.set_data_value(parameter=get_group_local_bonus_parameter(), round_data=round_data, value=local_bonus)

                group_cluster_conservation_hours += group_conservation_hours
            group_cluster_bonus = calculate_group_cluster_bonus(group_cluster_conservation_hours, group_cluster_threshold)
            group_cluster_bonus_dict[group_cluster] = group_cluster_bonus
            group_cluster.set_data_value(parameter=get_group_cluster_bonus_parameter(), round_data=round_data, value=group_cluster_bonus)
    ## needs revision:
        for group_cluster in GroupCluster.objects.for_experiment(experiment):
            for group_relationship in group_cluster.group_relationship_set.all():
                group = group_relationship.group
                for pgr in group.participant_group_relationship_set.all():
                    payoff = (participant_conservation_dict[pgr] * group_local_bonus_dict[group]) + \
                                         (get_harvest_decision(pgr, round_data) * group_cluster_bonus_dict[group_cluster])
                    pgr.set_data_value(parameter=get_payoff_parameter(), round_data=round_data, value=payoff)
