from vcweb.core.models import ExperimentMetadata, Parameter, Experiment
from vcweb.core import signals
import logging
logger = logging.getLogger(__name__)

def forestry_second_tick():
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''

def get_resource_level(group=None):
    return group.get_data_value(parameter_name='resource_level') if group else None

def get_harvest_decisions(group=None):
    return group.get_participant_data_values(parameter_name='harvest_decision') if group else []

def get_forestry_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='forestry')

def get_resource_level_parameter():
    return Parameter.objects.get(name='resource_level',
            scope=Parameter.GROUP_SCOPE,
            experiment_metadata=get_forestry_experiment_metadata()
            )

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
    else:
        '''
        practice or basic round, set up resource levels and participant
        harvest decision parameters
        '''
        if round_configuration.get_parameter('reset.resource_level'):
            for group in experiment.groups.all():
                ''' set resource level to default '''
                set_resource_level(group, round_configuration.get_parameter_value('initial.resource_level'))
        ''' initialize all participant data values '''
        current_round_data = experiment.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for p in experiment.participants.all():
            harvest_decision = current_round_data.participant_data_values.create(participant=p, parameter=harvest_decision_parameter)
            logger.debug("initialized harvest decision %s" % harvest_decision)

def round_teardown(experiment, **kwargs):
    round_configuration = experiment.current_round
    ''' calculate new resource levels '''
    resource_level_parameter = get_resource_level_parameter()

    for group in experiment.groups.all():
        total_harvest = sum( [ hd.value for hd in get_harvest_decisions(group).all() ])
        group.subtract(resource_level_parameter, total_harvest)
        if experiment.has_next_round:
            ''' set group round data resource_level for each group '''
            logger.debug("Transferring resource level %s to next round" %
                    get_resource_level(group))
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
forestry_sender = 'forestry'

signals.round_started.connect(round_started_handler, sender=forestry_sender)
signals.round_ended.connect(round_ended_handler, sender=forestry_sender)
