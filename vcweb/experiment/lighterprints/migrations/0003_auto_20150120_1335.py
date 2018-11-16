# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lighterprints', '0002_initial_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='cooldown',
            field=models.PositiveIntegerField(default=1, help_text='How much time must elapse before this activity becomes available again, in 1h intervals', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='activity',
            name='group_activity',
            field=models.BooleanField(default=False, help_text='Activity with shared group effect multipliers, e.g., ride sharing'),
            preserve_default=True,
        ),
    ]
