from django.db import models
from django.dispatch import receiver
from vcweb.core import signals, simplecache
from vcweb.core.models import Parameter, ParticipantRoundDataValue
from vcweb.forestry.models import get_harvest_decision_parameter, set_harvest_decision

import logging
logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = 'broker'

def get_max_harvest_hours(experiment):
    return experiment.experiment_configuration.get_parameter_value(name='max_hours', default=10).int_value

''' participant parameters '''
@simplecache
def get_participant_link_parameter():
    return Parameter.objects.get(name='participant_link')

@simplecache
def get_conservation_decision_parameter():
    return Parameter.objects.get(name='conservation_decision')

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

def set_conservation_decision(participant_group_relationship, value, round_data=None):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    prdv = ParticipantRoundDataValue.objects.get(parameter=get_conservation_decision_parameter(),
            participant_group_relationship=participant_group_relationship,
            round_data=round_data)
    prdv.int_value = value
    prdv.save()

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
                group_parameters=(get_group_local_bonus_parameter(), get_group_cluster_bonus_parameter()),
                participant_parameters=[get_harvest_decision_parameter(), get_conservation_decision_parameter(), get_participant_link_parameter()]
                )

@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    current_round_configuration = experiment.current_round
    logger.debug("ending boundaries round: %s", current_round_configuration)
