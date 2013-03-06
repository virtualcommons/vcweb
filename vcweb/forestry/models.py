from django.dispatch import receiver
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue)
from vcweb.core import signals, simplecache
import logging
logger = logging.getLogger(__name__)

def forestry_second_tick():
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''

def get_resource_level_dv(group, round_data=None, default=100):
    return group.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data, default=default)

def get_resource_level(group, round_data=None, **kwargs):
    ''' returns the group resource level data value scalar '''
    return get_resource_level_dv(group, round_data=round_data, **kwargs).int_value

def get_group_harvest(group, round_data=None):
    ''' returns the collective group harvest data value '''
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data).int_value

# returns the number of resources regenerated for the given group in the given round
def get_regrowth(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0).int_value

def get_regrowth_rate(current_round, default=0.1):
    return current_round.get_parameter_value(get_regrowth_rate_parameter(), default=default)

def has_resource_level(group=None):
    return group.has_data_parameter(parameter=get_resource_level_parameter())

# FIXME: revamp
def get_harvest_decision(participant_group_relationship, round_data=None):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    try:
        return ParticipantRoundDataValue.objects.get(participant_group_relationship=participant_group_relationship,
                round_data=round_data, parameter__name='harvest_decision')
    except ParticipantRoundDataValue.DoesNotExist:
        return None

def get_harvest_decisions(group=None):
    return group.get_participant_data_values(parameter__name='harvest_decision') if group else []

def set_regrowth(group, value):
    group.set_data_value(parameter=get_regrowth_parameter(), value=value)

def set_group_harvest(group, value):
    group.set_data_value(parameter=get_group_harvest_parameter(), value=value)

def should_reset_resource_level(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(), default=False).boolean_value

def get_initial_resource_level(round_configuration, default=100):
    return round_configuration.get_parameter_value(parameter=get_initial_resource_level_parameter(), default=default).int_value

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

@simplecache
def get_forestry_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='forestry')

@simplecache
def get_resource_level_parameter():
    return Parameter.objects.for_group(name='resource_level')

@simplecache
def get_regrowth_rate_parameter():
    return Parameter.objects.for_group(name='regrowth_rate')

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

def set_harvest_decision(participant_group_relationship=None, value=None):
    participant_group_relationship.set_data_value(parameter=get_harvest_decision_parameter(), value=value)

def set_resource_level(group, value, round_data=None):
    return group.set_data_value(parameter=get_resource_level_parameter(), round_data=round_data, value=value)

def round_setup(experiment, **kwargs):
    round_configuration = experiment.current_round
    logger.debug("setting up round %s", round_configuration)
    if round_configuration.is_playable_round:
        # participant parameter
        harvest_decision_parameter = get_harvest_decision_parameter()
        # group parameters
        regrowth_parameter = get_regrowth_parameter()
        group_harvest_parameter = get_group_harvest_parameter()
        resource_level_parameter = get_resource_level_parameter()
        # initialize group and participant data values
        experiment.initialize_parameters(
                group_parameters=(regrowth_parameter, group_harvest_parameter, resource_level_parameter),
                participant_parameters=[harvest_decision_parameter]
                )
        '''
        during a practice or regular round, set up resource levels and participant
        harvest decision parameters
        '''
        if should_reset_resource_level(round_configuration):
            initial_resource_level = get_initial_resource_level(round_configuration)
            logger.debug("Resetting resource level for %s to %d", round_configuration, initial_resource_level)
            round_data = experiment.current_round_data
            for group in experiment.group_set.all():
                ''' set resource level to initial default '''
                group.log("Setting resource level to initial value [%s]" % initial_resource_level)
                set_resource_level(group, initial_resource_level, round_data=round_data)

def round_teardown(experiment, **kwargs):
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    current_round_configuration = experiment.current_round
    logger.debug("current round: %s", current_round_configuration)
    max_resource_level = 100
    for group in experiment.group_set.all():
        # FIXME: simplify logic
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

'''
FIXME: figure out a better way to tie these signal handlers to a specific
ExperimentMetadata instance.  Using ExperimentMetadata.namespace is problematic
due to the python builtin id used by dispatcher.py and utf-8 strings...
for an example, try
e = Experiment.objects.get(pk=1)
id(e.namespace)
id(u'forestry')
id(repr(u'forestry'))
id(repr(e.namespace))
even using django.util.encodings smart_unicode and smart_str functions don't help.
'''
FORESTRY_SENDER = intern('forestry')
@receiver(signals.round_started, sender=FORESTRY_SENDER)
def round_started_handler(sender, experiment=None, **kwargs):
    round_setup(experiment, **kwargs)

@receiver(signals.round_ended, sender=FORESTRY_SENDER)
def round_ended_handler(sender, experiment=None, **kwargs):
    logger.debug("forestry handling round ended signal")
    round_teardown(experiment, **kwargs)



