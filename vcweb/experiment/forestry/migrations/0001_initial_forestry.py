# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations


def create_forestry_experiment_metadata(apps, schema_editor):
    ExperimentMetadata = apps.get_model('core', 'ExperimentMetadata')
    Experiment = apps.get_model('core', 'Experiment')
    Experimenter = apps.get_model('core', 'Experimenter')
    demo_experimenter = Experimenter.objects.get(user__email=settings.DEMO_EXPERIMENTER_EMAIL)
    forestry_experiment_metadata = ExperimentMetadata.objects.create(
        title='Forestry Experiment',
        namespace='forestry',
        about_url='http://commons.asu.edu',
        description='Web-based version of forestry field experiments conducted by Cardenas, Janssen, and Bousquet'
    )
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
    forestry_configuration.round_configuration_set.create(
        round_type='PRACTICE',
        sequence_number=3,
        repeat=2,
        initialize_data_values=True,
        randomize_groups=True
    )
    forestry_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=4,
        repeat=10,
        initialize_data_values=True,
        chat_enabled=True,
    )
    forestry_configuration.round_configuration_set.create(
        round_type='REGULAR',
        sequence_number=5,
        repeat=10,
        initialize_data_values=True,
        chat_enabled=False,
    )
    return forestry_configuration


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial_data'),
    ]

    operations = [
        migrations.RunPython(create_forestry_experiment_metadata)
    ]
