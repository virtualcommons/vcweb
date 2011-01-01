from vcweb.core.models import ExperimentMetadata, Parameter


# Create your models here.
def forestry_second_tick():
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''


def get_resource_level(group=None):
    return group.get_data_value(parameter_name='resource_level') if group else []

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
    for group in experiment.groups:
        total_harvest = sum( [ hd.value for hd in get_harvest_decisions(group).all() ])
        group.subtract(resource_level_parameter, total_harvest)



def round_setup():
    ''' get previous round harvest decisions initialize new group round data for all groups '''


