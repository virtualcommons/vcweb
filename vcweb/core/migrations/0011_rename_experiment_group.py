# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_activitylog_log_type'),
    ]

    operations = [
        migrations.operations.RenameModel('Group', 'ExperimentGroup')
    ]
