# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20150416_1602'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylog',
            name='log_type',
            field=models.CharField(default=b'System', max_length=64, choices=[(b'Experimenter', b'Experimenter'), (b'Scheduled', b'Scheduled'), (b'System', b'System')]),
        ),
    ]
