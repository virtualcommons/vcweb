from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

from vcweb.core.models import Participant, Experimenter, PermissionGroup

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Assigns users to respective permission group'

    def assign_group(self, lst, group):
        for item in lst:
            item.user.groups = [group]
            item.user.save()
            logger.debug(
                "User %s assigned to %s permissions group.", item.user, group)

    def handle(self, *args, **options):
        # first make sure all permission groups exist
        groups = {}
        for p in PermissionGroup:
            groups[p], created = Group.objects.get_or_create(name=p.value)
            if created:
                logger.warning(
                    "creating groups but this should normally be done via data migration.")

            # Adding permissions that are currently used in templates.
            # Need to revisit in future when more permissions are being used.
            if p == PermissionGroup.participant:
                perms = Permission.objects.filter(content_type__model='user')
                groups[p].permissions = perms
            elif p == PermissionGroup.experimenter:
                perms = Permission.objects.filter(content_type__model='experiment')
                groups[p].permissions = perms

        participant_list = Participant.objects.select_related(
            'user').exclude(user__email__regex=r'@mailinator.com$')
        experimenter_list = Experimenter.objects.select_related(
            'user').exclude(user__email__regex=r'@mailinator.com$')
        demo_participant_list = Participant.objects.select_related(
            'user').filter(user__email__regex=r'@mailinator.com$')
        demo_experimenter_list = Experimenter.objects.select_related(
            'user').filter(user__email__regex=r'@mailinator.com$')

        self.assign_group(
            participant_list, groups[PermissionGroup.participant])
        self.assign_group(
            demo_participant_list, groups[PermissionGroup.demo_participant])
        self.assign_group(
            experimenter_list, groups[PermissionGroup.experimenter])
        self.assign_group(
            demo_experimenter_list, groups[PermissionGroup.demo_experimenter])
