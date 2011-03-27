from django.contrib.auth.models import User
from vcweb.core.models import ExperimentMetadata, Parameter, ParticipantExperimentRelationship, ParticipantGroupRelationship, ParticipantRoundDataValue, Participant, Institution
from vcweb.core import signals
from celery.decorators import task
import logging
logger = logging.getLogger(__name__)

def forestry_second_tick():
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''


# returns GroupRoundDataValue.
def get_resource_level(group=None, round_data=None):
    return group.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data)

def get_group_harvest(group, round_data=None):
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data)

def get_regrowth(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data)

def has_resource_level(group=None):
    return group.has_data_parameter(parameter=get_resource_level_parameter())


def get_harvest_decision(participant_group_relationship, round_data=None):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    try:
        return ParticipantRoundDataValue.objects.get(participant_group_relationship=participant_group_relationship,
                round_data=round_data, parameter__name='harvest_decision')
    except ParticipantRoundDataValue.DoesNotExist:
        return None

def get_harvest_decisions(group=None):
    return group.get_participant_data_values(parameter_name='harvest_decision') if group else []

def set_regrowth(group, value):
    group.set_data_value(parameter=get_regrowth_parameter(), value=value)

def set_group_harvest(group, value):
    group.set_data_value(parameter=get_group_harvest_parameter(), value=value)

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

def get_forestry_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='forestry')

def get_resource_level_parameter():
    return Parameter.objects.get(name='resource_level',
            scope=Parameter.GROUP_SCOPE,
            experiment_metadata=get_forestry_experiment_metadata())

def get_regrowth_parameter():
    return Parameter.objects.get(name='group_regrowth',
            scope=Parameter.GROUP_SCOPE,
            experiment_metadata=get_forestry_experiment_metadata())

def get_group_harvest_parameter():
    return Parameter.objects.get(name='group_harvest',
            scope=Parameter.GROUP_SCOPE,
            experiment_metadata=get_forestry_experiment_metadata())

def get_harvest_decision_parameter():
    return Parameter.objects.get(
            name='harvest_decision',
            scope=Parameter.PARTICIPANT_SCOPE,
            experiment_metadata=get_forestry_experiment_metadata())

def set_harvest_decision(participant=None, experiment=None, value=None):
    participant.set_data_value(experiment=experiment, parameter=get_harvest_decision_parameter(), value=value)

def set_resource_level(group=None, value=None):
    group.set_data_value(parameter=get_resource_level_parameter(), value=value)

def round_setup(experiment, **kwargs):
    logger.debug("forestry: round_setup for %s" % experiment)
    round_configuration = experiment.current_round
    '''
    FIXME: replace with dict-based dispatch on round_configuration.round_type?
    '''
    if round_configuration.is_instructions_round:
        logger.debug("set up instructions round")
        # do instructions stuff
    elif round_configuration.is_quiz_round:
        logger.debug("setting up quiz round")
    elif round_configuration.is_chat_round:
        logger.debug("set up chat round")
    elif round_configuration.is_debriefing_round:
        logger.debug("set up debriefing round")

    if round_configuration.is_playable_round:
        '''
        practice or regular round, set up resource levels and participant
        harvest decision parameters
        '''
        if round_configuration.get_parameter_value('reset.resource_level', default=False):
            for group in experiment.groups.all():
                ''' set resource level to default '''
                set_resource_level(group, round_configuration.get_parameter_value('initial.resource_level'))
        ''' initialize all participant data values '''
        current_round_data = experiment.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for p in ParticipantGroupRelationship.objects.filter(group__experiment=experiment):
            harvest_decision, created = current_round_data.participant_data_values.get_or_create(participant_group_relationship=p, parameter=harvest_decision_parameter)
            logger.debug("%s harvest decision %s" % ("created" if created else "retrieved", harvest_decision))

@task
def stop_round_task():
    pass

def round_teardown(experiment, **kwargs):
    logger.debug("forestry: round_teardown for %s" % experiment)
    ''' only calculate new resource levels for practice or regular rounds '''
    resource_level_parameter = get_resource_level_parameter()
    current_round_configuration = experiment.current_round
# FIXME: make a round parameter for this.
    max_resource_level = 100
    for group in experiment.groups.all():
# implements regrowth function inline
        if has_resource_level(group):
            current_resource_level = get_resource_level(group)
            if current_round_configuration.is_playable_round:
                total_harvest = sum( [ hd.value for hd in get_harvest_decisions(group).all() ])
                if current_resource_level.value > 0 and total_harvest > 0:
                    group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level.value))
                    set_group_harvest(group, total_harvest)
                    current_resource_level.value = max(current_resource_level.value - total_harvest, 0)
                    #group.subtract(resource_level_parameter, total_harvest)
            ''' transfer resource levels across chat and quiz rounds if they exist '''
            if experiment.has_next_round:
                ''' set group round data resource_level for each group + regrowth '''
                regrowth = current_resource_level.value / 10
                group.log("Regrowth: adding %s to current resource level %s" % (regrowth, current_resource_level.value))
                set_regrowth(group, regrowth)
                current_resource_level.value = min(current_resource_level.value + regrowth, max_resource_level)
                current_resource_level.save()
                group.log("Transferring resource level %s to next round" % get_resource_level(group))
                group.transfer_to_next_round(resource_level_parameter)

#@receiver(signals.round_started, sender='forestry')
def round_started_handler(sender, experiment=None, **kwargs):
    logger.debug("forestry handling round started signal")
    round_setup(experiment, **kwargs)

#@receiver(signals.round_ended, sender='forestry')
def round_ended_handler(sender, experiment=None, **kwargs):
    logger.debug("forestry handling round ended signal")
    round_teardown(experiment, **kwargs)


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
forestry_sender = 1

signals.round_started.connect(round_started_handler, sender=forestry_sender)
signals.round_ended.connect(round_ended_handler, sender=forestry_sender)
