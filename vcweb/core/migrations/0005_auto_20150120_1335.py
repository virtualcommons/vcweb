# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20141030_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='experimentconfiguration',
            name='description',
            field=models.TextField(help_text='Description of experiment treatment', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='parameter',
            name='class_name',
            field=models.CharField(help_text='Signifies which model class a foreign key parameter is pointing to, e.g., "lighterprints.Activity"', max_length=64, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='roundconfiguration',
            name='preserve_existing_groups',
            field=models.BooleanField(default=True, help_text='When randomize_groups is set to true, archives any existing groups during randomization instead of deleting.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='roundconfiguration',
            name='repeat',
            field=models.PositiveIntegerField(default=0, help_text='This round will repeat n times with the same configuration and parameter values.'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='roundconfiguration',
            name='session_id',
            field=models.CharField(default=b'', help_text=" Session id to associate with this round data and the groups in this experiment, useful for longer\n    multi-session experiments where group membership may change.  We don't want to destroy the old groups as that\n    information is still needed to determine payments, etc. Instead we need to create a new set of\n    Group/ParticipantGroupRelationship models that can live in conjunction with the existing\n        Group/ParticipantGroupRelationship models. ", max_length=64, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='roundconfiguration',
            name='template_filename',
            field=models.CharField(help_text='The filename of the template to use to render when executing this round.\n    This file should exist in your templates directory as your-experiment-namespace/template-name.html, e.g., if set to\n    foo.html, vcweb will look for templates/forestry/foo.html', max_length=64, blank=True),
            preserve_default=True,
        ),
    ]
