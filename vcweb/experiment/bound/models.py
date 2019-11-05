import logging
import sys
from collections import defaultdict

from django.db import models, transaction
from django.dispatch import receiver

from vcweb.core import signals, simplecache
from vcweb.core.models import (DefaultValue, ExperimentMetadata, Parameter, ParticipantRoundDataValue,
                               GroupRelationship, RoundConfiguration, get_participant_ready_parameter)
from vcweb.experiment.forestry.models import (
    get_harvest_decision_parameter, get_harvest_decision, get_group_harvest_parameter,
    get_reset_resource_level_parameter, get_regrowth_parameter, get_initial_resource_level_parameter,
    set_resource_level as forestry_set_resource_level,
    set_harvest_decision as forestry_set_harvest_decision,
    get_resource_level_parameter, get_resource_level_dv as get_unshared_resource_level_dv,
    get_group_harvest_dv, get_regrowth_dv,)

logger = logging.getLogger(__name__)

# FIXME: hacky, figure out a better way to bind module with its dependent
# ExperimentMetadata instance
EXPERIMENT_METADATA_NAME = sys.intern('bound')
# constants that should live in configuration as well
MAX_RESOURCE_LEVEL = 240
MAX_SHARED_RESOURCE_LEVEL = 480

INITIAL_RESOURCES_PER_PARTICIPANT_PER_ROUND = 3

'''
Experiment parameters and metadata accessors
'''

set_harvest_decision = forestry_set_harvest_decision
set_resource_level = forestry_set_resource_level


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


@simplecache
def get_empty_resource_death_parameter():
    return Parameter.objects.for_round(name='empty_resource_death_enabled')


''' value accessors '''

''' round and experiment configuration accessors '''


def get_regrowth_rate(round_configuration):
    return round_configuration.get_parameter_value(name='regrowth_rate', default=0.40).float_value


# def is_empty_resource_death_enabled(round_configuration):
#    return round_configuration.get_parameter_value(parameter=get_empty_resource_death_parameter(),
#            default=False).boolean_value

def can_observe_other_group(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_observe_other_group_parameter(),
                                                   default=False).boolean_value


def is_shared_resource_enabled(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_shared_resource_enabled_parameter(),
                                                   default=False).boolean_value


def get_max_resource_level(round_configuration):
    initial_resource_level = get_initial_resource_level(round_configuration)
    if initial_resource_level is None:
        ec = round_configuration.experiment_configuration
        # FIXME: number of rounds currently hard coded to be 20 for regular
        # rounds, 10 for practice rounds
        number_of_rounds = 20 if round_configuration.is_regular_round else 10
        return INITIAL_RESOURCES_PER_PARTICIPANT_PER_ROUND * ec.max_group_size * number_of_rounds
    else:
        return initial_resource_level


def get_initial_resource_level(round_configuration, default=None):
    return round_configuration.get_parameter_value(parameter=get_initial_resource_level_parameter(),
                                                   default=default).int_value


def should_reset_resource_level(round_configuration, experiment):
    if round_configuration.is_repeating_round and experiment.current_repeated_round_sequence_number > 0:
        return False
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(),
                                                   default=False).boolean_value


def get_cost_of_living(round_configuration):
    return round_configuration.get_parameter_value(get_cost_of_living_parameter(), default=5).int_value


def get_max_harvest_decision(experiment_configuration):
    return experiment_configuration.get_parameter_value(parameter=get_max_harvest_decision_parameter(),
                                                        default=10).int_value


def get_resource_level(group, round_data=None, round_configuration=None, cluster=None):
    return get_resource_level_dv(group, round_data, round_configuration, cluster).int_value


''' group data accessors '''


def get_average_harvest(group, round_data):
    return get_total_group_harvest(group, round_data) / float(group.size)


def get_average_storage(group, round_data):
    return get_total_storage(group, round_data) / float(group.size)


def get_resource_level_dv(group, round_data=None, round_configuration=None, cluster=None, shared_resource_enabled=None):
    '''
    Returns either the GroupClusterDataValue (shared resource condition) or the GroupRoundDataValue (standard
    resource per group condition) for the given group
    '''
    if round_data is None:
        round_data = group.current_round_data
    if round_configuration is None:
        round_configuration = round_data.round_configuration
    if shared_resource_enabled is None:
        shared_resource_enabled = is_shared_resource_enabled(
            round_configuration)
    if shared_resource_enabled:
        return get_shared_resource_level_dv(group, round_data, cluster)
    else:
        return get_unshared_resource_level_dv(group, round_data)


def get_shared_resource_level(group, round_data=None, cluster=None):
    return get_shared_resource_level_dv(group, round_data, cluster).int_value


def get_shared_resource_level_dv(group=None, round_data=None, cluster=None):
    if round_data is None:
        round_data = group.current_round_data
    if cluster is None:
        group_relationship = GroupRelationship.objects.select_related('cluster').get(group=group)
        cluster = group_relationship.cluster
    return cluster.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data)


def get_shared_regrowth_dv(cluster=None, round_data=None):
    if round_data is None:
        round_data = cluster.experiment.current_round_data
    return cluster.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data)


def get_storage_dv(participant_group_relationship, round_data=None, default=None):
    return participant_group_relationship.get_data_value(parameter=get_storage_parameter(), round_data=round_data,
                                                         default=default)


def get_storage(participant_group_relationship, round_data=None, default=0):
    dv = get_storage_dv(participant_group_relationship, round_data, default)
    return max(default if dv.int_value is None else dv.int_value, 0)


def get_final_session_storage_queryset(experiment, participant):
    """
    Returns a QuerySet of the final storage ParticipantRoundDataValues for a given participant. For any given session,
    they can be found in the last round of the session, assumed to be the debriefing round.

    Query must be executed by participant as participant group relationship ids change when we re-randomize groups.
    """
    debriefing_session_round_data = experiment.round_data_set.filter(
        round_configuration__round_type=RoundConfiguration.RoundType.DEBRIEFING).exclude(
        round_configuration__session_id__exact='')
    session_storages = ParticipantRoundDataValue.objects.filter(
        participant_group_relationship__participant=participant,
        parameter=get_storage_parameter(),
        round_data__in=debriefing_session_round_data).order_by('date_created')
    # NOTE: assumes only 2 sessions
    if len(session_storages) == 2:
        return session_storages
    else:
        error_message = "bound: looking for 2 final session storages for participant %s in experiment %s but only found %s" % (
            participant, experiment, session_storages)
        logger.error(error_message)
        raise ParticipantRoundDataValue.DoesNotExist(error_message)


def _zero_if_none(value):
    return 0 if value is None else value


def get_total_group_harvest(group, round_data):
    q = ParticipantRoundDataValue.objects.for_group(group=group,
                                                    parameter=get_harvest_decision_parameter(),
                                                    round_data=round_data).aggregate(total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


def get_total_harvest(participant_group_relationship, session_id):
    q = ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
                                                          parameter=get_harvest_decision_parameter(),
                                                          participant_group_relationship__group__session_id=session_id).aggregate(
        total_harvest=models.Sum('int_value'))
    return _zero_if_none(q['total_harvest'])


def get_total_storage(group, round_data):
    """ returns the sum of all group member's storage for the given round """
    q = ParticipantRoundDataValue.objects.for_group(group=group,
                                                    parameter=get_storage_parameter(),
                                                    round_data=round_data).aggregate(
        total_storage=models.Sum('int_value'))
    return _zero_if_none(q['total_storage'])


def set_storage(participant_group_relationship, round_data, value):
    storage_dv = get_storage_dv(participant_group_relationship, round_data)
    storage_dv.update_int(value)
    return storage_dv


def get_player_status_dv(participant_group_relationship, round_data, default=True):
    return participant_group_relationship.get_data_value(parameter=get_player_status_parameter(),
                                                         round_data=round_data, default=default)


def is_player_alive(participant_group_relationship, round_data, default=True):
    return get_player_status_dv(participant_group_relationship, round_data, default).boolean_value


def get_number_alive(group, round_data):
    return ParticipantRoundDataValue.objects.for_group(group,
                                                       parameter=get_player_status_parameter(),
                                                       round_data=round_data,
                                                       boolean_value=True).count()


def get_player_data(group, previous_round_data, current_round_data, self_pgr):
    """ Returns a tuple ([list of player data dictionaries], { dictionary of this player's data })

     FIXME: refactor this into its own class as opposed to an arcane data structure
    """
    prdvs = ParticipantRoundDataValue.objects.for_group(group=group,
                                                        round_data__in=[
                                                            previous_round_data, current_round_data],
                                                        parameter__in=(get_player_status_parameter(),
                                                                       get_storage_parameter(),
                                                                       get_harvest_decision_parameter()))
    # nested dict mapping participant group relationship -> dict(parameter ->
    # participant round data value)
    player_dict = defaultdict(lambda: defaultdict(lambda: None))
    player_status_parameter = get_player_status_parameter()
    for prdv in prdvs:
        player_dict[prdv.participant_group_relationship][prdv.parameter] = prdv
    player_data = []
    for pgr, pgrdv_dict in list(player_dict.items()):
        # FIXME: figure out a way to handle default values elegantly in this case since we aren't using the accessor
        # methods
        for int_parameter in (get_harvest_decision_parameter(), get_storage_parameter()):
            if pgrdv_dict[int_parameter] is None:
                pgrdv_dict[int_parameter] = DefaultValue(0)
        if pgrdv_dict[player_status_parameter] is None:
            pgrdv_dict[player_status_parameter] = DefaultValue(True)
        player_data.append({
            'id': pgr.pk,
            'number': pgr.participant_number,
            'lastHarvestDecision': pgrdv_dict[get_harvest_decision_parameter()].int_value,
            'alive': pgrdv_dict[get_player_status_parameter()].boolean_value,
            'storage': pgrdv_dict[get_storage_parameter()].int_value
        })
    own_player = player_dict[self_pgr]
    return (player_data, {
        'lastHarvestDecision': own_player[get_harvest_decision_parameter()].int_value,
        'alive': own_player[get_player_status_parameter()].boolean_value,
        'storage': own_player[get_storage_parameter()].int_value
    })


@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_started_handler(sender, experiment=None, **kwargs):
    if experiment is None:
        logger.error(
            "Received round started signal with no experiment: %s", sender)
        raise ValueError("Received round started signal with no experiment")
    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("setting up round %s", round_configuration)
    # initialize group, group cluster, and participant data values
    experiment.initialize_data_values(
        group_cluster_parameters=(get_regrowth_parameter(), get_resource_level_parameter()),
        group_parameters=(get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter()),
        participant_parameters=(get_storage_parameter(), get_player_status_parameter()),
        defaults={
            get_storage_parameter(): 0,
            get_player_status_parameter(): True,
        }
    )
    shared_resource_enabled = is_shared_resource_enabled(round_configuration)
    if should_reset_resource_level(round_configuration, experiment):
        initial_resource_level = get_max_resource_level(round_configuration)
        logger.debug("Resetting resource level for all groups in %s to %d",
                     round_configuration, initial_resource_level)
        for group in experiment.groups:
            # set resource level to initial default
            existing_resource_level = get_resource_level_dv(group, round_data, round_configuration,
                                                            shared_resource_enabled=shared_resource_enabled)
            group.log("Resetting resource level (%s) to initial value [%s]" %
                      (existing_resource_level, initial_resource_level))
            existing_resource_level.update_int(initial_resource_level)
            # zero out all participant storages when the resource level is
            # reset
            ParticipantRoundDataValue.objects.for_group(group, parameter=get_storage_parameter(),
                                                        round_data=round_data).update(int_value=0)
            # set all player statuses to alive when the resource level is reset
            ParticipantRoundDataValue.objects.for_group(group, parameter=get_player_status_parameter(),
                                                        round_data=round_data).update(boolean_value=True)
    elif round_configuration.is_playable_round:
        # first check for a depleted resource
        # FIXME: currently disabled again as per Tim's instructions
        # if is_empty_resource_death_enabled():
        #     for group in experiment.groups:
        #         existing_resource_level = get_resource_level_dv(group, round_data, round_configuration,
        #                                                         shared_resource_enabled=shared_resource_enabled)
        #         if existing_resource_level.int_value <= 0:
        #             group.log("depleted resource %s, zeroing out all harvest decisions and marking all group members as deceased" % existing_resource_level)
        #             participant_group_relationship_pks = group.participant_group_relationship_set.values_list('pk', flat=True)
        #             _zero_harvest_decisions(participant_group_relationship_pks,  round_data)
        # depleted resource kills all participants in that group
        #             ParticipantRoundDataValue.objects.filter(parameter=get_player_status_parameter(),
        #                     participant_group_relationship__pk__in=participant_group_relationship_pks,
        #                     round_data=round_data).update(boolean_value=False)
        #             ParticipantRoundDataValue.objects.filter(parameter=get_storage_parameter(),
        #                     participant_group_relationship__pk__in=participant_group_relationship_pks,
        #                     round_data=round_data).update(int_value=0)
        # FIXME: redundant when resource is depleted, needs refactor
        # check for dead participants and set their ready and harvest decision flags
        deceased_participants = ParticipantRoundDataValue.objects.filter(
            parameter=get_player_status_parameter(),
            round_data=round_data,
            boolean_value=False).values_list('participant_group_relationship', flat=True)
        _zero_harvest_decisions(deceased_participants, round_data)


def _zero_harvest_decisions(participant_group_relationship_ids, round_data):
    data_values = ParticipantRoundDataValue.objects.with_parameter(
        get_harvest_decision_parameter(), round_data=round_data,
        participant_group_relationship__pk__in=participant_group_relationship_ids)
    data_values.update(int_value=0, submitted=True)
    data_values = ParticipantRoundDataValue.objects.with_parameter(
        get_participant_ready_parameter(), round_data=round_data,
        participant_group_relationship__pk__in=participant_group_relationship_ids)
    data_values.update(boolean_value=True)
    '''
    for dv in data_values:
        if dv.parameter == get_harvest_decision_parameter():
            dv.update_int(0, submitted=True)
        elif dv.parameter == get_participant_ready_parameter():
            dv.update_boolean(True)
    '''


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
    logger.debug("total number of decisions: %s - group size: %s",
                 total_number_of_decisions, group_size)
    decisions_allocated = 0
    for hd in hds:
        if hd.int_value <= average_harvest:
            group.log("preserving %s < average harvest" % hd)
            total_adjusted_harvest += hd.int_value
        else:
            # now to assign the overs, find out how much resource level is
            # remaining
            remaining_resource_level = current_resource_level - \
                total_adjusted_harvest
            remaining_decisions = total_number_of_decisions - \
                decisions_allocated
            average_harvest = remaining_resource_level / remaining_decisions
            hd.is_active = False
            hd.save()
            logger.debug("Assigning %s to hd %s", average_harvest, hd)
            ParticipantRoundDataValue.objects.create(participant_group_relationship=hd.participant_group_relationship,
                                                     parameter=get_harvest_decision_parameter(), round_data=round_data,
                                                     int_value=average_harvest,
                                                     submitted=True)
            total_adjusted_harvest += average_harvest
        decisions_allocated += 1

    logger.debug("harvested total %s", total_adjusted_harvest)
    return total_adjusted_harvest


@transaction.atomic
def update_resource_level(experiment, group, round_data, regrowth_rate, max_resource_level=None):
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(
            round_data.round_configuration)
    current_resource_level_dv = get_resource_level_dv(
        group, round_data, shared_resource_enabled=False)
    current_resource_level = current_resource_level_dv.int_value
    group_harvest_dv = get_group_harvest_dv(group, round_data)
    regrowth_dv = get_regrowth_dv(group, round_data)
    # FIXME: would be nicer to extend Group behavior and have group.get_total_harvest() instead of
    # get_total_group_harvest(group, ...), see if we can enable this
    # dynamically
    total_harvest = get_total_group_harvest(group, round_data)
    logger.debug("Harvest: total group harvest for playable round: %s", total_harvest)
    if current_resource_level > 0:
        if total_harvest > current_resource_level:
            adjusted_harvest = adjust_harvest_decisions(
                current_resource_level, group, round_data, total_harvest)
            total_harvest = adjusted_harvest

        group.log("Harvest: removing %s from current resource level %s" %
                  (total_harvest, current_resource_level))
        group_harvest_dv.update_int(total_harvest)
        current_resource_level = current_resource_level - total_harvest
        resource_regrowth = calculate_regrowth(current_resource_level, regrowth_rate, max_resource_level)
        group.log("Regrowth: adding %s to current resource level %s" %
                  (resource_regrowth, current_resource_level))
        regrowth_dv.update_int(resource_regrowth)
        # clamp resource
        current_resource_level_dv.update_int(
            min(current_resource_level + resource_regrowth, max_resource_level))
    else:
        group.log("current resource level is 0, no one can harvest")
        group_harvest_dv.update_int(0)
        ParticipantRoundDataValue.objects.for_group(group, parameter=get_harvest_decision_parameter(),
                                                    round_data=round_data).update(is_active=False)
        for pgr in group.participant_group_relationship_set.all():
            # Create adjusted data values
            ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr,
                                                     round_data=round_data, parameter=get_harvest_decision_parameter(
                                                     ),
                                                     int_value=0)
    ''' XXX: transfer resource levels across chat and quiz rounds if they exist '''
    if experiment.has_next_round:
        ''' set group round data resource_level for each group + regrowth '''
        group.log("Transferring resource level %s to next round" %
                  current_resource_level_dv.int_value)
        group.copy_to_next_round(current_resource_level_dv, group_harvest_dv, regrowth_dv)


# FIXME: reduce duplication between this and update_resource_level
@transaction.atomic
def update_shared_resource_level(experiment, group_cluster, round_data, regrowth_rate, max_resource_level=None):
    logger.debug("updating shared resource level")
    if max_resource_level is None:
        max_resource_level = get_max_resource_level(
            round_data.round_configuration)
    max_resource_level = max_resource_level * group_cluster.size
    shared_resource_level_dv = get_shared_resource_level_dv(
        cluster=group_cluster, round_data=round_data)
    shared_resource_level = shared_resource_level_dv.int_value
    shared_regrowth_dv = get_shared_regrowth_dv(
        cluster=group_cluster, round_data=round_data)
    # FIXME: set up shared group harvest parameter as well
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
    for group, group_harvest in list(group_harvest_dict.items()):
        if shared_group_harvest > shared_resource_level:
            # adjust each individual harvest for each group in this cluster
            group_harvest = adjust_harvest_decisions(shared_resource_level, group, round_data, group_harvest,
                                                     group_size=group_cluster_size)
        # set_group_harvest(group, group_harvest, round_data)
        shared_resource_level = shared_resource_level - group_harvest
    # set regrowth after shared_resource_level has been modified by all groups
    # in this cluster
    resource_regrowth = calculate_regrowth(shared_resource_level, regrowth_rate, max_resource_level)
    group.log("Regrowth: adding %s to shared resource level %s" % (resource_regrowth, shared_resource_level))
    shared_regrowth_dv.update_int(resource_regrowth)
    # group_cluster.set_data_value(parameter=get_regrowth_parameter(), round_data=round_data, value=resource_regrowth)
    # clamp resource level to max_resource_level
    shared_resource_level_dv.update_int(min(shared_resource_level + resource_regrowth, max_resource_level))
    if experiment.has_next_round:
        ''' transfer shared resource levels to next round '''
        group.log("Transferring shared resource level %s to next round" %
                  shared_resource_level_dv.int_value)
        group_cluster.copy_to_next_round(shared_resource_level_dv, shared_regrowth_dv)


@transaction.atomic
def update_participants(experiment, round_data, round_configuration):
    logger.debug("updating participants")
    cost_of_living = get_cost_of_living(round_configuration)
    next_round_data, created = experiment.get_or_create_round_data(round_configuration=experiment.next_round,
                                                                   increment_repeated_round_sequence_number=True)
    for group in experiment.groups:
        for pgr in group.participant_group_relationship_set.all():
            player_status_dv = get_player_status_dv(pgr, round_data)
            storage_dv = get_storage_dv(pgr, round_data)
            player_alive = player_status_dv.boolean_value
            if player_alive:
                harvest_decision = get_harvest_decision(pgr, round_data)
                logger.error("storage dv %s harvest decision %s cost of living %s", storage_dv.int_value, harvest_decision,
                             cost_of_living)
                updated_storage = storage_dv.int_value + harvest_decision - cost_of_living
                if updated_storage < 0:
                    # player has "died"
                    player_status_dv.update_boolean(False)
                # clamp storage to 0 to avoid negative earnings
                storage_dv.update_int(max(0, updated_storage))
            pgr.copy_to_next_round(player_status_dv, storage_dv, next_round_data=next_round_data)


@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_ended_handler(sender, experiment=None, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    round_configuration = experiment.current_round
    round_data = experiment.get_round_data(round_configuration)
    logger.debug("ending boundary effects round: %s", round_configuration)
    try:
        if round_configuration.is_playable_round:
            regrowth_rate = get_regrowth_rate(round_configuration)
            harvest_decision_parameter = get_harvest_decision_parameter()
            for pgr in experiment.participant_group_relationships:
                # FIXME: not thread-safe but this *should* only be invoked once per experiment. If we start getting
                # spurious data values, revisit this section
                prdvs = ParticipantRoundDataValue.objects.filter(
                    round_data=round_data,
                    participant_group_relationship=pgr,
                    parameter=harvest_decision_parameter,
                    is_active=True)
                number_of_harvest_decisions = prdvs.count()
                if number_of_harvest_decisions == 0:
                    # create zero harvest decisions for any unsubmitted harvest decisions
                    ParticipantRoundDataValue.objects.create(round_data=round_data,
                                                             participant_group_relationship=pgr,
                                                             parameter=harvest_decision_parameter,
                                                             is_active=True,
                                                             int_value=0)
                    logger.debug("autozero harvest decision for participant %s", pgr)
                elif number_of_harvest_decisions > 1:
                    # deactivate all prior harvest decisions
                    logger.debug("multiple harvest decisions found for %s, deactivating all but the latest", pgr)
                    final_harvest_decision = prdvs.latest('date_created')
                    prdvs.exclude(pk=final_harvest_decision.pk).update(is_active=False)

            # FIXME: generify and merge update_shared_resource_level and
            # update_resource_level to operate on "group-like" objects if
            # possible
            if is_shared_resource_enabled(round_configuration):
                for group_cluster in experiment.active_group_clusters:
                    update_shared_resource_level(experiment, group_cluster, round_data, regrowth_rate)
            else:
                for group in experiment.groups:
                    update_resource_level(experiment, group, round_data, regrowth_rate)
            update_participants(experiment, round_data, round_configuration)
    except:
        logger.exception('Failed to end round cleanly')


def calculate_regrowth(resource_level, regrowth_rate, max_resource_level):
    if resource_level >= max_resource_level:
        return 0
    logger.debug("calculating regrowth: (%s * %s) * (1 - (%s / %s))", regrowth_rate, resource_level, resource_level,
                 max_resource_level)
    return (regrowth_rate * resource_level) * (1 - (resource_level / float(max_resource_level)))
