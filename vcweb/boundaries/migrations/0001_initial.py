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
        # XXX: set up parameters and configuration as well in the migration?
        RoundConfiguration = orm['core.RoundConfiguration']
        rc = RoundConfiguration.objects.create(
                experiment_configuration=ec,
                instructions='Welcome to the boundary effects experiment.',
                round_type=RoundConfiguration.INSTRUCTIONS
                )

    def backwards(self, orm):
        ExperimentMetadata = orm['core.ExperimentMetadata']
        ExperimentMetadata.objects.get(namespace='bound').delete()

    models = {

            }

    complete_apps = ['boundaries']
