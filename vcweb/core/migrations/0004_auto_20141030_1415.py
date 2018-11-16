# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20140919_1512'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experimentsession',
            name='location',
            field=models.CharField(help_text='Where will this experiment session be held?', max_length=128),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='participantexperimentrelationship',
            name='participant_identifier',
            field=models.CharField(max_length=64),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='participantsignup',
            name='attendance',
            field=models.PositiveIntegerField(default=3, max_length=1, choices=[(0, 'participated'), (1, 'turned away'), (2, 'absent'), (3, 'signed up'), (4, 'waitlisted')]),
            preserve_default=True,
        ),
    ]
