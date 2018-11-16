# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_experimentconfiguration_payment_information'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experimentconfiguration',
            name='exchange_rate',
            field=models.DecimalField(decimal_places=2, default=0.02, max_digits=6, blank=True, help_text='Exchange rate of currency per in-game token, dollars per token', null=True),
            preserve_default=True,
        ),
    ]
