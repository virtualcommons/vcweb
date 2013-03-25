from django.db.models import Sum
from django.dispatch import receiver
from vcweb.core import signals, simplecache
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue, GroupRelationship, GroupCluster, GroupClusterDataValue)
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision, get_regrowth_rate,
                                   get_group_harvest_parameter, get_reset_resource_level_parameter, get_resource_level,
                                   get_initial_resource_level as forestry_initial_resource_level, set_resource_level, get_regrowth_parameter,
                                   get_resource_level_parameter, has_resource_level, get_resource_level_dv as get_unshared_resource_level_dv, get_harvest_decisions,
                                   set_group_harvest, set_regrowth)

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


def can_observe_other_group(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_observe_other_group_parameter(),
                                                   default=False).boolean_value


def is_shared_resource_enabled(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_shared_resource_enabled_parameter(),
                                                   default=False).boolean_value


def get_resource_level_dv(group, round_data=None, round_configuration=None):
    '''
    Returns either the GroupClusterDataValue (shared resource condition) or the GroupRoundDataValue (standard
    resource per group condition) for the given group
    '''
    if round_data is None:
        round_data = group.current_round_data
    if round_configuration is None:
        round_configuration = round_data.round_configuration
    if is_shared_resource_enabled(round_configuration):
        return get_shared_resource_level_dv(group, round_data)
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


def get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL):
    return forestry_initial_resource_level(round_configuration, default)


def get_max_harvest(experiment):
    return experiment.get_parameter_value(parameter=get_max_harvest_decision_parameter(), default=10).int_value


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
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(),
                                                   default=False).boolean_value


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
        initial_resource_level = get_initial_resource_level(round_configuration)
        logger.debug("Resetting resource level for %s to %d", round_configuration, initial_resource_level)
        round_data = experiment.get_round_data(round_configuration)
        for group in experiment.group_set.all():
            ''' set resource level to initial default '''
            existing_resource_level = get_resource_level_dv(group, round_data, round_configuration)
            group.log(
                "Setting resource level (%s) to initial value [%s]" % (existing_resource_level, initial_resource_level))
            existing_resource_level.int_value = initial_resource_level
            existing_resource_level.save()


def get_total_harvest(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(
        group=group,
        parameter=get_harvest_decision_parameter(),
        round_data=round_data).aggregate(total_harvest=Sum('int_value'))
    return q['total_harvest']


def adjust_harvest_decisions(current_resource_level, group, group_size, round_data, total_harvest):
    individual_harvest = current_resource_level / group_size
    adjusted_harvest = individual_harvest * group_size
    group.log(
            "GROUP HARVEST ADJUSTMENT - original total harvest: %s, resource level: %s, individual harvest: %s, adjusted group harvest: %s" %
        (total_harvest, current_resource_level, individual_harvest, adjusted_harvest))
    # deactivate old participant round data value decisions
    ParticipantRoundDataValue.objects.for_group(group=group,
                                                parameter=get_harvest_decision_parameter(),
                                                round_data=round_data).update(is_active=False)
    # create new harvest decision data values
    for pgr in group.participant_group_relationship_set.all():
        ParticipantRoundDataValue.objects.create(round_data=round_data,
                                                 participant_group_relationship=pgr,
                                                 parameter=get_harvest_decision_parameter(),
                                                 int_value=individual_harvest)
    return adjusted_harvest


def adjust_resource_level(experiment, group, round_data, max_resource_level=MAX_RESOURCE_LEVEL):
    current_resource_level_dv = get_resource_level_dv(group)
    current_resource_level = current_resource_level_dv.int_value
    total_harvest = get_total_harvest(group, round_data)
    logger.debug("total harvest for playable round: %d", total_harvest)
    if current_resource_level > 0 and total_harvest > 0:
        if total_harvest > current_resource_level:
            # divide remaining trees evenly among every participant
            group_size = group.size
            adjusted_harvest = adjust_harvest_decisions(current_resource_level, group, group_size, round_data,
                                                        total_harvest)
            total_harvest = adjusted_harvest

        group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
        set_group_harvest(group, total_harvest, round_data)
        current_resource_level = current_resource_level - total_harvest
        resource_regrowth = calculate_regrowth(current_resource_level)
        group.log("Regrowth: adding %s to current resource level %s" % (resource_regrowth, current_resource_level))
        set_regrowth(group, resource_regrowth, round_data)
        current_resource_level_dv.int_value = min(current_resource_level + resource_regrowth, max_resource_level)
        current_resource_level_dv.save()
    ''' XXX: transfer resource levels across chat and quiz rounds if they exist '''
    if experiment.has_next_round:
        ''' set group round data resource_level for each group + regrowth '''
        group.log("Transferring resource level %s to next round" % current_resource_level_dv.int_value)
        group.copy_to_next_round(current_resource_level_dv)


# FIXME: a lot of duplication between this and adjust_resource_level, see if we can reduce it by operating on group
# cluster data values instead of group data values
def adjust_shared_resource_level(experiment, group_cluster, round_data, max_resource_level=MAX_RESOURCE_LEVEL):
    shared_resource_level_dv = get_shared_resource_level_dv(cluster=group_cluster, round_data=round_data)
    shared_resource_level = shared_resource_level_dv.int_value
    shared_group_harvest = 0
    total_group_size = 0
    group_harvest_dict = {}
    for group_relationship in group_cluster.group_relationship_set.all():
        group = group_relationship.group
        total_group_size += group.size
        group_harvest = get_total_harvest(group, round_data)
        group_harvest_dict[group] = group_harvest
        shared_group_harvest += group_harvest
        group.log("total group harvest: %s" % group_harvest)
    for group, group_harvest in group_harvest_dict.items():
        if shared_group_harvest > shared_resource_level:
        # adjust each individual harvest for each group in this cluster
            group_harvest = adjust_harvest_decisions(shared_resource_level, group, total_group_size, round_data, group_harvest)
        set_group_harvest(group, group_harvest, round_data)
        shared_resource_level = shared_resource_level - group_harvest
    # set regrowth after shared_resource_level has been modified by all groups in this cluster
    resource_regrowth = calculate_regrowth(shared_resource_level)
    group.log("Regrowth: adding %s to shared resource level %s" % (resource_regrowth, shared_resource_level))
    group_cluster.set_data_value(parameter=get_regrowth_parameter(), round_data=round_data,
            value=resource_regrowth)
    shared_resource_level_dv.int_value = min(shared_resource_level + resource_regrowth, max_resource_level)
    shared_resource_level_dv.save()
    if experiment.has_next_round:
        ''' transfer shared resource levels to next round '''
        group_cluster.copy_to_next_round(shared_resource_level_dv)


@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("ending boundaries round: %s", round_configuration)
    # FIXME: need to clarify logic for keeping track of resource levels across rounds
    if round_configuration.is_playable_round:
        if is_shared_resource_enabled(round_configuration):
            for group_cluster in GroupCluster.objects.for_experiment(experiment,
                                                                     session_id=round_configuration.session_id):
                adjust_shared_resource_level(experiment, group_cluster, round_data)
        else:
            for group in experiment.group_set.all():
                adjust_resource_level(experiment, group, round_data)


def calculate_regrowth(resource_level):
    # FIXME: re-implement based on Tim's logic, this is leftover from forestry
    return resource_level / 10
