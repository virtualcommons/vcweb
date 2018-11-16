# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lighterprints', '0003_auto_20150120_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='mptt_level',
            field=models.PositiveIntegerField(default=0, editable=False, db_index=True),
            preserve_default=False,
        ),
    ]
