# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-16 07:16


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lighterprints', '0004_activity_mptt_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='icon',
            field=models.ImageField(upload_to='lighterprints/activity-icons/'),
        ),
    ]