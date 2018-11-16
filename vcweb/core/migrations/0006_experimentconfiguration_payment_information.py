# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20150120_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='experimentconfiguration',
            name='payment_information',
            field=models.TextField(help_text='Markdown formatted payment information to be displayed to a participant at the conclusion of this experiment', blank=True),
            preserve_default=True,
        ),
    ]
