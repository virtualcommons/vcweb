# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import models, migrations


def create_forestry_experiment_metadata(apps, schema_editor):
    ExperimentMetadata = apps.get_model('core', 'ExperimentMetadata')
    Experiment = apps.get_model('core', 'Experiment')
    Experimenter = apps.get_model('core', 'Experimenter')
    demo_experimenter = Experimenter.objects.get(
        user__email=settings.DEMO_EXPERIMENTER_EMAIL)
    forestry_experiment_metadata = ExperimentMetadata.objects.create(
        title='Forestry Experiment',
        namespace='forestry',
        about_url='http://commons.asu.edu',
        description='Web-based version of forestry field experiments conducted by Cardenas, Janssen, and Bousquet'
    )
    parameters = create_forestry_parameters(apps, schema_editor)
    forestry_experiment_metadata.parameters.add(*parameters)
    forestry_configuration = create_forestry_configuration(apps, schema_editor,
                                                           experiment_metadata=forestry_experiment_metadata,
                                                           experimenter=demo_experimenter)
    forestry_experiment = Experiment.objects.create(
        experiment_configuration=forestry_configuration,
        experiment_metadata=forestry_experiment_metadata,
        experimenter=demo_experimenter,
    )


def create_forestry_configuration(apps, schema_editor, experiment_metadata=None, experimenter=None):
    ExperimentConfiguration = apps.get_model('core', 'ExperimentConfiguration')
    Parameter = apps.get_model('core', 'Parameter')
    initial_resource_level_param = Parameter.objects.get(name='initial_resource_level')
    reset_resource_level_param = Parameter.objects.get(name='reset_resource_level')

    forestry_configuration = ExperimentConfiguration.objects.create(
        name='Slovakia NC/C',
        is_public=True,
        max_group_size=5,
        is_experimenter_driven=True,
        creator=experimenter,
        experiment_metadata=experiment_metadata
    )
    forestry_configuration.round_configuration_set.create(
        round_type='WELCOME',
        sequence_number=1
    )
    forestry_configuration.round_configuration_set.create(
        round_type='GENERAL_INSTRUCTIONS',
        sequence_number=2
    )
    practice_round = forestry_configuration.round_configuration_set.create(
        round_type='PRACTICE',
        sequence_number=3,
        repeat=2,
        initialize_data_values=True,
    )
    practice_round.parameter_value_set.create(
        parameter=reset_resource_level_param,
        boolean_value=True,
    )
    practice_round.parameter_value_set.create(
        parameter=initial_resource_level_param,
        int_value=100,
    )
    first_repeating_round = forestry_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=4,
        repeat=10,
        initialize_data_values=True,
        chat_enabled=True,
    )
    first_repeating_round.parameter_value_set.create(
        parameter=reset_resource_level_param,
        boolean_value=True,
    )
    first_repeating_round.parameter_value_set.create(
        parameter=initial_resource_level_param,
        int_value=100,
    )
    second_repeating_round = forestry_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=5,
        repeat=10,
        initialize_data_values=True,
        chat_enabled=False,
    )
    second_repeating_round.parameter_value_set.create(
        parameter=reset_resource_level_param,
        boolean_value=True,
    )
    second_repeating_round.parameter_value_set.create(
        parameter=initial_resource_level_param,
        int_value=100,
    )
    forestry_configuration.round_configuration_set.create(
        round_type='DEBRIEFING',
        sequence_number=6,
    )
    return forestry_configuration


def create_forestry_parameters(apps, schema_editor):
    Parameter = apps.get_model('core', 'Parameter')
    return [
        Parameter.objects.create(
            name='initial_resource_level',
            display_name='Initial resource level',
            description='Initial number of resources to set at the beginning of the round. Will only be set if reset_resource_level is true',
            scope='round',
            type='int',
            default_value_string='100',
        ),
        Parameter.objects.create(
            name='reset_resource_level',
            display_name='Reset resource level?',
            description='Set to true if you want to set the resource level to the initial resource level at the beginning of this round',
            scope='round',
            type='boolean',
            default_value_string='false',
        ),
        Parameter.objects.create(
            name='regrowth',
            display_name='Resource regrowth',
            description='Amount of resource regrowth for a given group in a given round',
            scope='group',
            type='int',
        ),
        Parameter.objects.create(
            name='resource_level',
            display_name='Resource level',
            description='Integer value representing the resource level for the given group in the given round',
            scope='group',
            type='int',
        ),
        Parameter.objects.create(
            name='group_harvest',
            display_name='Total group harvest',
            description='Total number of trees harvested by the given group in the given round',
            scope='group',
            type='int',
        ),
        Parameter.objects.create(
            name='regrowth_rate',
            display_name='Resource regrowth rate',
            description='''Resource regrowth scaling factor, a floating point number between 0 and 1. The forestry experiment uses a simple regrowth function, N*r + N, where N is the current resource level and r is the regrowth rate. ''',
            scope='round',
            type='float',
        ),
        Parameter.objects.create(
            name='harvest_decision',
            display_name='Participant harvest decision',
            description='Number of resources this participant elected to harvest this round.',
            scope='participant',
            type='int',
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial_data'),
    ]

    operations = [
        migrations.RunPython(create_forestry_experiment_metadata),
    ]
