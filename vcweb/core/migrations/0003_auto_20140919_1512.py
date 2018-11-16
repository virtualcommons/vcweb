# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parameter',
            name='description',
            field=models.TextField(blank=True),
        ),
    ]
