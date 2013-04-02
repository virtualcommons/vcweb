from django.db.models import Sum
from django.dispatch import receiver
from vcweb.core import signals, simplecache
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue, GroupRelationship, GroupCluster, GroupClusterDataValue)
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision, get_harvest_decision_dv, get_regrowth_rate_parameter,
                                   get_group_harvest_parameter, get_reset_resource_level_parameter, get_resource_level as get_unshared_resource_level,
                                   get_initial_resource_level as forestry_initial_resource_level, get_regrowth_parameter, set_resource_level,
                                   get_resource_level_parameter, get_resource_level_dv as get_unshared_resource_level_dv,
                                   set_group_harvest, set_regrowth, set_harvest_decision)

import logging

logger = logging.getLogger(__name__)

# FIXME: hacky, should figure out a better way to bind this module with the ExperimentMetadata instance that it is
# dependent on
EXPERIMENT_METADATA_NAME = intern('bound')
# constants that should live in configuration as well
MAX_RESOURCE_LEVEL = 240
MAX_SHARED_RESOURCE_LEVEL = 480

RESOURCES_PER_PARTICIPANT = 60

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
    return Parameter.objects.for_experiment(name='max_harvest_decision')


@simplecache
def get_cost_of_living_parameter():
    return Parameter.objects.for_round(name='cost_of_living')


@simplecache
def get_observe_other_group_parameter():
    return Parameter.objects.for_round(name='observe_other_group')


@simplecache
def get_shared_resource_enabled_parameter():
    return Parameter.objects.for_round(name='shared_resource')


''' value accessors '''

''' round and experiment configuration accessors '''
def get_regrowth_rate(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_regrowth_rate_parameter(), default=0.40).float_value


def can_observe_other_group(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_observe_other_group_parameter(),
                                                   default=False).boolean_value


def is_shared_resource_enabled(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_shared_resource_enabled_parameter(),
                                                   default=False).boolean_value

def get_max_resource_level(experiment_configuration):
    return RESOURCES_PER_PARTICIPANT * experiment_configuration.max_group_size

def get_initial_resource_level(round_configuration, default=None):
    return get_max_resource_level(round_configuration.experiment_configuration)

def should_reset_resource_level(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(),
                                                   default=False).boolean_value

def get_cost_of_living(round_configuration):
    return round_configuration.get_parameter_value(get_cost_of_living_parameter(), default=5).int_value


def get_max_harvest_decision(experiment_configuration):
    return experiment_configuration.get_parameter_value(parameter=get_max_harvest_decision_parameter(), default=10).int_value

def get_max_allowed_harvest_decision(participant_group_relationship, round_data=None, experiment_configuration=None):
    return get_max_harvest_decision(experiment_configuration)

def get_resource_level(group, round_data=None, round_configuration=None, cluster=None):
    return get_resource_level_dv(group, round_data, round_configuration, cluster).int_value

''' group data accessors '''
def get_average_harvest(group, round_data):
    return get_total_group_harvest(group, round_data) / float(group.size)

def get_average_storage(group, round_data):
    return get_total_storage(group, round_data) / float(group.size)

def get_resource_level_dv(group, round_data=None, round_configuration=None, cluster=None):
    '''
    Returns either the GroupClusterDataValue (shared resource condition) or the GroupRoundDataValue (standard
    resource per group condition) for the given group
    '''
    if round_data is None:
        round_data = group.current_round_data
    if round_configuration is None:
        round_configuration = round_data.round_configuration
    if is_shared_resource_enabled(round_configuration):
        return get_shared_resource_level_dv(group, round_data, cluster)
    else:
        return get_unshared_resource_level_dv(group, round_data)


def get_shared_resource_level(group, round_data=None, cluster=None):
    return get_shared_resource_level_dv(group, round_data, cluster).int_value


def get_shared_resource_level_dv(group=None, round_data=None, cluster=None):
    if round_data is None:
        round_data = group.current_round_data
    if cluster is None:
        group_relationship = GroupRelationship.objects.select_related('group_cluster').get(group=group)
        cluster = group_relationship.cluster
    return cluster.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data)

''' participant data value accessors '''

def get_storage_dv(participant_group_relationship, round_data=None, default=None):
    return participant_group_relationship.get_data_value(parameter=get_storage_parameter(), round_data=round_data, default=default)


def get_storage(participant_group_relationship, round_data=None, default=0):
    dv = get_storage_dv(participant_group_relationship, round_data, default)
    return max(default if dv.int_value is None else dv.int_value, 0)


def _zero_if_none(value):
    return 0 if value is None else value

def get_total_group_harvest(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(group=group, parameter=get_harvest_decision_parameter(), round_data=round_data).aggregate(total_harvest=Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


def get_total_harvest(participant_group_relationship, session_id):
    q = ParticipantRoundDataValue.objects.for_participant(participant_group_relationship, parameter=get_harvest_decision_parameter(),
            participant_group_relationship__group__session_id=session_id).aggregate(total_harvest=Sum('int_value'))
    return _zero_if_none(q['total_harvest'])

# returns the sum of all stored resources for each member in the group
def get_total_storage(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(group=group, parameter=get_storage_parameter(), round_data=round_data).aggregate(total_storage=Sum('int_value'))
    return _zero_if_none(q['total_storage'])

def set_storage(participant_group_relationship, round_data, value):
    storage_dv = get_storage_dv(participant_group_relationship, round_data)
    storage_dv.int_value = value
    storage_dv.save()
    return storage_dv

def get_player_status_dv(participant_group_relationship, round_data, default=True):
    return participant_group_relationship.get_data_value(parameter=get_player_status_parameter(),
            round_data=round_data, default=default)

def get_player_status(participant_group_relationship, round_data, default=True):
    return get_player_status_dv(participant_group_relationship, round_data, default).boolean_value

def set_player_status(participant_group_relationship, round_data, value):
    status_dv =  get_player_status_dv(participant_group_relationship, round_data)
    status_dv.boolean_value = value
    status_dv.save()
    return status_dv

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
    if round_configuration.is_playable_round:
        experiment.initialize_data_values(
            group_cluster_parameters=(get_regrowth_parameter(), get_resource_level_parameter(),),
            group_parameters=(get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter(),),
            participant_parameters=(get_harvest_decision_parameter(), get_storage_parameter(),
                                    get_player_status_parameter(),)
        )
    '''
    during a practice or regular round, set up resource levels, participant harvest decision parameters, and group
    formation
    '''
    if should_reset_resource_level(round_configuration):
        initial_resource_level = get_max_resource_level(round_configuration.experiment_configuration)
        logger.debug("Resetting resource level for %s to %d", round_configuration, initial_resource_level)
        round_data = experiment.get_round_data(round_configuration)
        for group in experiment.group_set.filter(session_id=round_configuration.session_id):
            ''' set resource level to initial default '''
            existing_resource_level = get_resource_level_dv(group, round_data, round_configuration)
            group.log(
                "Setting resource level (%s) to initial value [%s]" % (existing_resource_level, initial_resource_level))
            existing_resource_level.int_value = initial_resource_level
            existing_resource_level.save()
            # FIXME: make sure that this is expected behavior - if the resource level is reset, reset storage to 0
            ParticipantRoundDataValue.objects.for_group(group, parameter=get_storage_parameter(),
                    round_data=round_data).update(int_value=0)
            # reset all player statuses to True
            ParticipantRoundDataValue.objects.for_group(group, parameter=get_player_status_parameter(),
                    round_data=round_data).update(boolean_value=True)



def adjust_harvest_decisions(current_resource_level, group, round_data, total_harvest, group_size=0):
    if group_size == 0:
        group_size = group.size
# pass in the group size to handle group cluster case
    average_harvest = current_resource_level / group_size
    group.log("GROUP HARVEST ADJUSTMENT - original total harvest: %s, resource level: %s, average harvest: %s" %
        (total_harvest, current_resource_level, average_harvest))
    hds = ParticipantRoundDataValue.objects.for_group(group=group, parameter=get_harvest_decision_parameter(),
            round_data=round_data, int_value__gt=0).order_by('int_value')
    total_adjusted_harvest = 0
# FIXME: should be the same as group.size
    total_number_of_decisions = hds.count()
    logger.debug("total number of decisions: %s - group size: %s", total_number_of_decisions, group_size)
    decisions_allocated = 0
    for hd in hds:
        if hd.int_value <= average_harvest:
            group.log("preserving %s < average harvest" % hd)
            total_adjusted_harvest += hd.int_value
        else:
# now to assign the overs, find out how much resource level is remaining
            remaining_resource_level = current_resource_level - total_adjusted_harvest
            remaining_decisions = total_number_of_decisions - decisions_allocated
            average_harvest = remaining_resource_level / remaining_decisions
            hd.is_active = False
            hd.save()
            logger.debug("Assigning %s to hd %s", average_harvest, hd)
            ParticipantRoundDataValue.objects.create(participant_group_relationship=hd.participant_group_relationship,
                    parameter=get_harvest_decision_parameter(), round_data=round_data, int_value=average_harvest,
                    submitted=True)
            total_adjusted_harvest += average_harvest
        decisions_allocated += 1

    logger.debug("harvested total %s", total_adjusted_harvest)
    return total_adjusted_harvest


def update_resource_level(experiment, group, round_data, regrowth_rate, max_resource_level=None):
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(experiment.experiment_configuration)
    current_resource_level_dv = get_resource_level_dv(group, round_data)
    current_resource_level = current_resource_level_dv.int_value
# FIXME: would be nicer to extend Group behavior and have group.get_total_harvest() instead of
# get_total_group_harvest(group, ...), see if we can enable this dynamically
    total_harvest = get_total_group_harvest(group, round_data)
    logger.debug("Harvest: total group harvest for playable round: %s", total_harvest)
    if current_resource_level > 0:
        if total_harvest > current_resource_level:
            adjusted_harvest = adjust_harvest_decisions(current_resource_level, group, round_data, total_harvest)
            total_harvest = adjusted_harvest

        group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
        set_group_harvest(group, total_harvest, round_data)
        current_resource_level = current_resource_level - total_harvest
        resource_regrowth = calculate_regrowth(current_resource_level, regrowth_rate, max_resource_level)
        group.log("Regrowth: adding %s to current resource level %s" % (resource_regrowth, current_resource_level))
        set_regrowth(group, resource_regrowth, round_data)
        current_resource_level_dv.int_value = min(current_resource_level + resource_regrowth, max_resource_level)
        current_resource_level_dv.save()
    else:
        group.log("current resource level is 0, no one can harvest")
        set_group_harvest(group, 0, round_data)
        ParticipantRoundDataValue.objects.for_group(group, parameter=get_harvest_decision_parameter(),
                round_data=round_data).update(is_active=False)
        for pgr in group.participant_group_relationship_set.all():
            # Create adjusted data values
            ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr,
                    round_data=round_data, parameter=get_harvest_decision_parameter(),
                    int_value=0)


    ''' XXX: transfer resource levels across chat and quiz rounds if they exist '''
    if experiment.has_next_round:
        ''' set group round data resource_level for each group + regrowth '''
        group.log("Transferring resource level %s to next round" % current_resource_level_dv.int_value)
        group.copy_to_next_round(current_resource_level_dv)


# FIXME: try to reduce duplication between this and update_resource_level
def update_shared_resource_level(experiment, group_cluster, round_data, regrowth_rate, max_resource_level=None):
    logger.debug("updating shared resource level")
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(experiment.experiment_configuration)
    max_resource_level = max_resource_level * group_cluster.size
    shared_resource_level_dv = get_shared_resource_level_dv(cluster=group_cluster, round_data=round_data)
    shared_resource_level = shared_resource_level_dv.int_value
    shared_group_harvest = 0
    group_cluster_size = 0
    group_harvest_dict = {}
    for group_relationship in group_cluster.group_relationship_set.all():
        group = group_relationship.group
        group_cluster_size += group.size
        group_harvest = get_total_group_harvest(group, round_data)
        group_harvest_dict[group] = group_harvest
        shared_group_harvest += group_harvest
        group.log("total group harvest: %s" % group_harvest)
    for group, group_harvest in group_harvest_dict.items():
        if shared_group_harvest > shared_resource_level:
        # adjust each individual harvest for each group in this cluster
            group_harvest = adjust_harvest_decisions(shared_resource_level, group, round_data, group_harvest, group_size=group_cluster_size)
        set_group_harvest(group, group_harvest, round_data)
        shared_resource_level = shared_resource_level - group_harvest
    # set regrowth after shared_resource_level has been modified by all groups in this cluster
    resource_regrowth = calculate_regrowth(shared_resource_level, regrowth_rate, max_resource_level)
    group.log("Regrowth: adding %s to shared resource level %s" % (resource_regrowth, shared_resource_level))
    group_cluster.set_data_value(parameter=get_regrowth_parameter(), round_data=round_data, value=resource_regrowth)
    shared_resource_level_dv.int_value = min(shared_resource_level + resource_regrowth, max_resource_level)
    shared_resource_level_dv.save()
    if experiment.has_next_round:
        ''' transfer shared resource levels to next round '''
        group.log("Transferring shared resource level %s to next round" % shared_resource_level_dv.int_value)
        group_cluster.copy_to_next_round(shared_resource_level_dv)

def update_participants(experiment, round_data):
    logger.debug("updating participants")
    cost_of_living = get_cost_of_living(round_data.round_configuration)
    for pgr in experiment.participant_group_relationships:
        player_status_dv = get_player_status_dv(pgr, round_data)
        storage_dv = get_storage_dv(pgr, round_data)
        player_alive = player_status_dv.boolean_value
        if player_alive:
            harvest_decision = get_harvest_decision(pgr, round_data)
            updated_storage = storage_dv.int_value + harvest_decision - cost_of_living
            if updated_storage < 0:
                # player has "died"
                player_status_dv.boolean_value = False
                player_status_dv.save()
            storage_dv.int_value = updated_storage
            storage_dv.save()
            logger.debug("updating participant %s (storage: %s, harvest: %s, status: %s)", pgr, storage_dv.int_value,
                    harvest_decision, player_status_dv.boolean_value)
        pgr.copy_to_next_round(player_status_dv, storage_dv)

@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("ending boundaries round: %s", round_configuration)
    if round_configuration.is_playable_round:
        regrowth_rate = get_regrowth_rate(round_configuration)
        # zero out unsubmitted harvest decisions
        ParticipantRoundDataValue.objects.filter(round_data=round_data, parameter=get_harvest_decision_parameter(),
                submitted=False).update(int_value=0)
        # FIXME: generify and merge update_shared_resource_level and update_resource_level to operate on "group-like" objects if possible
        if is_shared_resource_enabled(round_configuration):
            for group_cluster in GroupCluster.objects.for_experiment(experiment, session_id=round_configuration.session_id):
                update_shared_resource_level(experiment, group_cluster, round_data, regrowth_rate)
        else:
            for group in experiment.group_set.filter(session_id=round_configuration.session_id):
                update_resource_level(experiment, group, round_data, regrowth_rate)
        update_participants(experiment, round_data)


def calculate_regrowth(resource_level, regrowth_rate, max_resource_level=240):
    return (regrowth_rate * resource_level) * (1 - (resource_level / float(max_resource_level)))

