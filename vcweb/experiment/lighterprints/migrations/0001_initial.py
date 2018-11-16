# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
from django.conf import settings
import mptt.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=32)),
                ('display_name', models.CharField(
                    max_length=64, null=True, blank=True)),
                ('summary', models.CharField(max_length=256)),
                ('description', models.TextField()),
                ('url', models.URLField()),
                ('savings', models.DecimalField(
                    default=0.0, max_digits=5, decimal_places=2)),
                ('points', models.PositiveIntegerField(default=0)),
                ('available_all_day', models.BooleanField(default=False)),
                ('personal_benefits', models.TextField(null=True, blank=True)),
                ('level', models.PositiveIntegerField(default=1)),
                ('group_activity', models.BooleanField(
                    default=False, help_text=b'Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')),
                ('cooldown', models.PositiveIntegerField(
                    default=1, help_text=b'How much time, in hours, must elapse before this activity can become available again', null=True, blank=True)),
                ('icon', models.ImageField(
                    upload_to=b'lighterprints/activity-icons/')),
                ('date_created', models.DateTimeField(
                    default=datetime.datetime.now)),
                ('last_modified', models.DateTimeField(
                    default=datetime.datetime.now)),
                ('is_public', models.BooleanField(default=False)),
                ('lft', models.PositiveIntegerField(
                    editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(
                    editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(
                    editable=False, db_index=True)),
                ('creator', models.ForeignKey(
                    blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('parent', mptt.fields.TreeForeignKey(
                    related_name=b'children_set', blank=True, to='lighterprints.Activity', null=True)),
            ],
            options={
                'ordering': ['level', 'name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ActivityAvailability',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start_time', models.TimeField(null=True, blank=True)),
                ('end_time', models.TimeField(null=True, blank=True)),
                ('activity', models.ForeignKey(
                    related_name=b'availability_set', to='lighterprints.Activity')),
            ],
            options={
                'ordering': ['activity', 'start_time'],
            },
            bases=(models.Model,),
        ),
    ]
