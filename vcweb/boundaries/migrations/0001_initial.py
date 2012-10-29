# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        ExperimentMetadata = orm['core.ExperimentMetadata']
        em = ExperimentMetadata.objects.create(title='Boundary Effects Experiment',
                namespace='bound',
                description='The boundary effect experiment manipulates the resource flows and information connections between social groups and ecological resources.',
                about_url='http://commons.asu.edu',
                )
        ExperimentConfiguration = orm['core.ExperimentConfiguration']
        Experimenter = orm['core.Experimenter']
        ec = ExperimentConfiguration.objects.create(
                namespace='bound',
                experiment_metadata=em,
                is_public=True,
                max_group_size=10,
                name='Boundary Effects Default Configuration',
                )
        em.default_configuration = ec
        em.save()
        Experiment = orm['core.Experiment']
        e = Experiment.objects.create(
                experiment_metadata=em,
                authentication_code='DEFAULT_BOUNDARIES',
                experimenter=Experimenter.objects.get(pk=1),
                is_experimenter_driven=True)
        # XXX: set up parameters and configuration as well in this migration
        Parameter = orm['core.Parameter']
        Parameter.objects.create(
                name='player_status',
                type='boolean',
                experiment_metadata=em,
                scope='participant',
                display_name='Player status',
                description='Player status (true = alive, false = dead)',
                )
        Parameter.objects.create(
                name='survival_cost',
                type='int',
                experiment_metadata=em,
                scope='round',
                display_name='Survival cost',
                description='The minimum number of resources each player needs to have in storage each round to survive',
                )
        Parameter.objects.create(
                name='storage',
                type='int',
                experiment_metadata=em,
                scope='participant',
                display_name='Storage',
                description='The number of resources this player has accumulated.',
                )

# create round configurations
        RoundConfiguration = orm['core.RoundConfiguration']
        RoundConfiguration.objects.create(
                experiment_configuration=ec,
                instructions='Welcome to the boundary effects experiment.',
                round_type='INSTRUCTIONS',
                sequence_number=1,
                )
        RoundConfiguration.objects.create(
                experiment_configuration=ec,
                instructions='This is the first practice round.',
                round_type='PRACTICE',
                sequence_number=2,
                display_number=1,
                )



    def backwards(self, orm):
        ExperimentMetadata = orm['core.ExperimentMetadata']
        ExperimentMetadata.objects.get(namespace='bound').delete()

    models = {

            }

    complete_apps = ['boundaries']
