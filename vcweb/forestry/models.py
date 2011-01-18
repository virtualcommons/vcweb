from vcweb.core.models import ExperimentMetadata, Parameter
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
    return group.get_participant_data_values(name='harvest_decision') if group else []

def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='forestry')

def get_resource_level_parameter():
    return Parameter.objects.get(name='resource_level',
            scope=Parameter.GROUP_SCOPE,
            experiment_metadata=get_experiment_metadata()
            )

def get_harvest_decision_parameter():
    return Parameter.objects.get(
            name='harvest_decision',
            scope=Parameter.PARTICIPANT_SCOPE,
            experiment_metadata=get_experiment_metadata())

def set_harvest_decision(participant=None, experiment=None, value=None):
    participant.set_data_value(experiment=experiment, parameter=get_harvest_decision_parameter(), value=value)

def set_resource_level(group=None, value=None):
    group.set_data_value(parameter=get_resource_level_parameter(), value=value)

def round_ended(experiment):
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

def round_setup(experiment):
    round_configuration = experiment.current_round
    if round_configuration.get_parameter('reset.resource_level'):
        for group in experiment.groups.all():
            ''' set resource level to default '''
            set_resource_level(group, round_configuration.get_parameter_value('initial.resource_level'))
            ''' initialize all participant data values '''
            for p in group.participants.all():
                harvest_decision, just_created = p.data_values.get_or_create(round_configuration=round_configuration, 
                        parameter=get_harvest_decision_parameter(),
                        experiment=experiment)
                logger.debug("initialized harvest decision %s (%s) for %s" 
                        % (harvest_decision, just_created, p))


