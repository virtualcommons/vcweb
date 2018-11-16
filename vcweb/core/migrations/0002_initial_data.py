# -*- coding: utf-8 -*-


from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import models, migrations

from vcweb.core.models import PermissionGroup

import logging


logger = logging.getLogger(__name__)


class DemoExperimenter(object):

    @staticmethod
    def forward(apps, schema_editor):
        Institution = apps.get_model('core', 'Institution')
        Experimenter = apps.get_model('core', 'Experimenter')
        User = apps.get_model('auth', 'User')
        Group = apps.get_model('auth', 'Group')
        asu = Institution.objects.create(
            name='Arizona State University',
            url='http://www.asu.edu',
            acronym='ASU',
            cas_server_url='https://weblogin.asu.edu/cas/'
        )
        demo_experimenter_user = User.objects.create(
            username=settings.DEMO_EXPERIMENTER_EMAIL,
            first_name='Vcweb Demo',
            last_name='Experimenter',
            email=settings.DEMO_EXPERIMENTER_EMAIL,
        )
        demo_experimenter_user.password = make_password('demo expr')
        demo_experimenter_user.save()
        groups = {}
        for p in PermissionGroup:
            groups[p] = Group.objects.create(name=p)
        demo_experimenter_user.groups.add(groups[PermissionGroup.demo_experimenter])
        Experimenter.objects.create(user=demo_experimenter_user, approved=True, institution=asu)

    @staticmethod
    def rollback(apps, schema_editor):
        Experimenter = apps.get_model('core', 'Experimenter')
        User = apps.get_model('auth', 'User')
        demo_experimenter_user = User.objects.get(username=settings.DEMO_EXPERIMENTER_EMAIL)
        Experimenter.objects.get(user=demo_experimenter_user).delete()
        demo_experimenter_user.delete()


class InitialParticipantParameters(object):

    @staticmethod
    def forward(apps, schema_editor):
        Parameter = apps.get_model('core', 'Parameter')
        Parameter.objects.create(
            name='participant_ready',
            display_name='Participant is ready',
            scope='participant',
            type='boolean',
            description='Flag signaling that this participant is ready to move on to the next round'
        )
        Parameter.objects.create(
            name='chat_message',
            display_name='Chat message',
            scope='participant',
            type='string',
            description='Chat message that can be broadcast to multiple participants or targeted to a specific participant',
        )
        Parameter.objects.create(
            name='like',
            display_name='Like',
            scope='participant',
            type='string',
            description='Like, like'
        )
        Parameter.objects.create(
            name='comment',
            display_name='Comment',
            scope='participant',
            type='string',
            description='Comment attached to some other participant data value (e.g., an activity performed or harvest decision)',
        )

    @staticmethod
    def rollback(apps, schema_editor):
        Parameter = apps.get_model('core', 'Parameter')
        Parameter.objects.filter(
            name__in=('participant_ready', 'chat_message', 'like', 'comment')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(DemoExperimenter.forward, DemoExperimenter.rollback),
        migrations.RunPython(InitialParticipantParameters.forward, InitialParticipantParameters.rollback),
    ]
