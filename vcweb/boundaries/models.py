from django.dispatch import receiver
from vcweb.core import signals, simplecache
from vcweb.core.models import ExperimentMetadata, Parameter, ParticipantRoundDataValue
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision, get_regrowth_rate,
        get_group_harvest_parameter, get_resource_level, get_initial_resource_level as forestry_initial_resource_level,
        set_resource_level, get_regrowth_parameter, get_resource_level_parameter, has_resource_level,
        get_resource_level_dv, get_harvest_decisions, set_group_harvest, set_regrowth)

import logging

logger = logging.getLogger(__name__)

# FIXME: hacky, should figure out a better way to bind this module with the ExperimentMetadata instance that it is
# dependent on that leaves the data in a single place. per-app settings files that define experiment metadata
# singletons?
EXPERIMENT_METADATA_NAME = intern('bound')
MAX_RESOURCE_LEVEL = 240

'''
Experiment Parameters and Metadata Accessors
'''
@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace=EXPERIMENT_METADATA_NAME)

@simplecache
def get_player_status_parameter():
    return Parameter.objects.for_participant(name='player_status')

@simplecache
def get_storage_parameter():
    return Parameter.objects.for_participant(name='storage')

@simplecache
def get_survival_cost_parameter():
    return Parameter.objects.for_round(name='survival_cost')

@simplecache
def get_max_harvest_decision_parameter():
    return Parameter.objects.for_round(name='max_harvest_decision')

@simplecache
def get_cost_of_living_parameter():
    return Parameter.objects.for_round(name='cost_of_living')

@simplecache
def get_observe_other_group_parameter():
    return Parameter.objects.for_round(name='observe_other_group')

@simplecache
def get_shared_resource_parameter():
    return Parameter.objects.for_round(name='shared_resource')

def can_observe_other_group(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_observe_other_group_parameter(), default=False).boolean_value

# players can either be dead or alive
def get_player_status_dv(participant_group_relationship_id):
    return ParticipantRoundDataValue.objects.get(parameter=get_player_status_parameter(), participant_group_relationship__pk=participant_group_relationship_id)


''' value accessors '''

def get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL):
    return forestry_initial_resource_level(round_configuration, default)

def get_cost_of_living(current_round):
    return current_round.get_parameter_value(get_cost_of_living_parameter(), default=5).int_value

def get_storage_dv(participant_group_relationship, round_data=None):
    return participant_group_relationship.get_data_value(parameter=get_storage_parameter(), round_data=round_data)

def get_storage(participant_group_relationship, round_data=None):
    return get_storage_dv(participant_group_relationship, round_data).int_value

# returns the sum of all stored resources for each member in the group
def get_total_storage(group):
    # FIXME: int_value would be more performant but storage isn't being initialized properly yet and value returns an
    # appropriate default value
    return sum([pdv.value for pdv in group.get_participant_data_values(parameter=get_storage_parameter())])

def set_storage(participant_group_relationship, value=0):
    storage_dv = participant_group_relationship.set_data_value(parameter=get_storage_parameter(), value=value)
    logger.debug("set storage variable: %s", storage_dv)
    return storage_dv

def should_reset_resource_level(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(), default=False).boolean_value

def get_last_harvest_decision(participant_group_relationship, round_data=None):
    return participant_group_relationship.get_data_value(parameter=get_harvest_decision_parameter(),
            round_data=round_data, default=0).int_value

@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
def round_started_handler(sender, experiment=None, **kwargs):
    if experiment is None:
        logger.error("Received round started signal with no experiment: %s", sender)
        raise ValueError("Received round started signal with no experiment")
    round_configuration = experiment.current_round
    logger.debug("setting up round %s", round_configuration)
    # initialize group and participant data values
    experiment.initialize_data_values(
            group_parameters=(get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter()),
            participant_parameters=[get_harvest_decision_parameter(), get_storage_parameter(), get_player_status_parameter()]
            )
    '''
    during a practice or regular round, set up resource levels and participant
    harvest decision parameters
    '''

    if should_reset_resource_level(round_configuration):
        initial_resource_level = get_initial_resource_level(round_configuration)
        logger.debug("Resetting resource level for %s to %d", round_configuration, initial_resource_level)
        round_data = experiment.get_round_data(round_configuration)
        for group in experiment.group_set.all():
            ''' set resource level to initial default '''
            group.log("Setting resource level to initial value [%s]" % initial_resource_level)
            set_resource_level(group, initial_resource_level, round_data=round_data)

@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    current_round_configuration = experiment.current_round
    logger.debug("ending boundaries round: %s", current_round_configuration)
# FIXME: max resource level might need to be read from the experiment / round configuration instead
    max_resource_level = MAX_RESOURCE_LEVEL
    for group in experiment.group_set.all():
        logger.debug("group %s has resource level", group)
        if has_resource_level(group):
            current_resource_level_dv = get_resource_level_dv(group)
            current_resource_level = current_resource_level_dv.int_value
            if current_round_configuration.is_playable_round:
                total_harvest = sum( [ hd.value for hd in get_harvest_decisions(group).all() ])
                logger.debug("total harvest for playable round: %d", total_harvest)
                if current_resource_level > 0 and total_harvest > 0:
                    group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
                    set_group_harvest(group, total_harvest)
                    current_resource_level = max(current_resource_level - total_harvest, 0)
                    # implements regrowth function inline
                    # FIXME: parameterize regrowth rate.
                    regrowth = current_resource_level / 10
                    group.log("Regrowth: adding %s to current resource level %s" % (regrowth, current_resource_level))
                    set_regrowth(group, regrowth)
                    current_resource_level_dv.int_value = min(current_resource_level + regrowth, max_resource_level)
                    current_resource_level_dv.save()
            ''' transfer resource levels across chat and quiz rounds if they exist '''
            if experiment.has_next_round:
                ''' set group round data resource_level for each group + regrowth '''
                group.log("Transferring resource level %s to next round" % current_resource_level_dv.int_value)
                group.copy_to_next_round(current_resource_level_dv)
