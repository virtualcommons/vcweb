# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_experimentsession_waitlist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participantsignup',
            name='attendance',
            field=models.PositiveIntegerField(default=3, choices=[(0, 'participated'), (1, 'turned away'), (2, 'absent'), (3, 'signed up'), (4, 'waitlisted')]),
        ),
    ]
