# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import models, migrations


def initial_boundary_effects_data(apps, schema_editor):
    ExperimentMetadata = apps.get_model('core', 'ExperimentMetadata')
    Experiment = apps.get_model('core', 'Experiment')
    Experimenter = apps.get_model('core', 'Experimenter')
    boundary_experiment_metadata = ExperimentMetadata.objects.create(
        title='Boundary Effects',
        namespace='bound',
        description='The boundary effects experiment manipulates the resource flows and information connections between social groups and ecological resources. Developed by Dr. Tim Waring, University of Maine'
    )
    parameters = create_boundary_effects_parameters(apps, schema_editor)
    demo_experimenter = Experimenter.objects.get(
        user__email=settings.DEMO_EXPERIMENTER_EMAIL)
    boundary_experiment_metadata.parameters.add(*parameters)
    boundary_configuration = create_boundary_configuration(apps, schema_editor,
                                                           experiment_metadata=boundary_experiment_metadata,
                                                           experimenter=demo_experimenter)
    boundary_experiment = Experiment.objects.create(
        experiment_configuration=boundary_configuration,
        experiment_metadata=boundary_experiment_metadata,
        experimenter=demo_experimenter,
    )


def create_boundary_configuration(apps, schema_editor, experiment_metadata=None, experimenter=None):
    ExperimentConfiguration = apps.get_model('core', 'ExperimentConfiguration')
    Parameter = apps.get_model('core', 'Parameter')

    initial_resource_level = Parameter.objects.get(
        name='initial_resource_level')
    reset_resource_level = Parameter.objects.get(name='reset_resource_level')
    observe_other_group = Parameter.objects.get(name='observe_other_group')
    shared_resource = Parameter.objects.get(name='shared_resource')

    boundary_configuration = ExperimentConfiguration.objects.create(
        name='Boundary Effects AB',
        is_public=True,
        max_group_size=4,
        is_experimenter_driven=True,
        creator=experimenter,
        experiment_metadata=experiment_metadata
    )
    boundary_configuration.round_configuration_set.create(
        round_type='WELCOME',
        sequence_number=1)
    boundary_configuration.round_configuration_set.create(
        round_type='GENERAL_INSTRUCTIONS',
        sequence_number=2)
    rc = boundary_configuration.round_configuration_set.create(
        round_type='PRACTICE',
        sequence_number=3,
        repeat=6,
        duration=60,
        initialize_data_values=True,
    )
    rc.parameter_value_set.create(
        parameter=initial_resource_level,
        int_value=120,
    )
    rc.parameter_value_set.create(
        parameter=reset_resource_level,
        boolean_value=True
    )
    boundary_configuration.round_configuration_set.create(
        round_type='DEBRIEFING',
        template_id='PRACTICE_ROUND_RESULTS',
        sequence_number=4,
    )
    boundary_configuration.round_configuration_set.create(
        round_type='INSTRUCTIONS',
        template_id='TREATMENT_A_INSTRUCTIONS',
        sequence_number=5,
        create_group_clusters=True,
        randomize_groups=True,
        session_id='A',
    )
    rc = boundary_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=6,
        repeat=10,
        session_id='A',
        initialize_data_values=True,
        duration=60
    )
    rc.parameter_value_set.create(
        parameter=shared_resource, boolean_value=True)
    rc.parameter_value_set.create(
        parameter=initial_resource_level, int_value=240)
    rc.parameter_value_set.create(
        parameter=reset_resource_level, boolean_value=True)
    rc.parameter_value_set.create(
        parameter=observe_other_group, boolean_value=True)
    boundary_configuration.round_configuration_set.create(
        round_type='DEBRIEFING',
        template_id='TREATMENT_RESULTS',
        sequence_number=7,
        session_id='A',
    )
    boundary_configuration.round_configuration_set.create(
        round_type='INSTRUCTIONS',
        template_id='TREATMENT_A_INSTRUCTIONS',
        sequence_number=8,
        randomize_groups=True,
        session_id='B',
    )
    rc = boundary_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=9,
        repeat=10,
        session_id='B',
        initialize_data_values=True,
        duration=60
    )
    rc.parameter_value_set.create(
        parameter=initial_resource_level, int_value=240)
    rc.parameter_value_set.create(
        parameter=reset_resource_level, boolean_value=True)
    rc.parameter_value_set.create(
        parameter=observe_other_group, boolean_value=False)
    boundary_configuration.round_configuration_set.create(
        round_type='DEBRIEFING',
        template_id='FINAL_DEBRIEFING',
        session_id='B',
        sequence_number=10,
    )
    return boundary_configuration


def create_boundary_effects_parameters(apps, schema_editor):
    Parameter = apps.get_model('core', 'Parameter')
    return [
        Parameter.objects.create(
            name='player_status',
            display_name='Player status',
            description='Boolean signifying whether this player is alive (true) or dead (false)',
            type='boolean',
            scope='participant'
        ),
        Parameter.objects.create(
            name='storage',
            display_name='Storage',
            description='Amount of resources accumulated by a participant across all played rounds.',
            type='int',
            scope='participant'
        ),
        Parameter.objects.create(
            name='cost_of_living',
            display_name='Cost of living',
            description='Number of resources in player storage required to survive each round.',
            type='int',
            scope='round',
        ),
        Parameter.objects.create(
            name='shared_resource',
            display_name='Shared resource?',
            description='Boolean signifying whether the given round should set up a single shared resource for each group cluster.',
            type='boolean',
            scope='round',
        ),
        Parameter.objects.create(
            name='max_harvest_decision',
            display_name='Max harvest decision',
            description='The maximum number of resources a participant can harvest in each round.',
            type='int',
            scope='experiment',
        ),
        Parameter.objects.create(
            name='observe_other_group',
            display_name='Observe other group?',
            description='Boolean signifying whether this group can observe the other group',
            type='boolean',
            scope='round',
        ),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ('forestry', '0001_initial_forestry'),
    ]

    operations = [
        migrations.RunPython(initial_boundary_effects_data)
    ]
