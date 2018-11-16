# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_auto_20150205_1544'),
    ]

    operations = [
        migrations.AddField(
            model_name='experimentsession',
            name='waitlist',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
