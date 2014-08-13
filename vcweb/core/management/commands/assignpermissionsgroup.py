from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from vcweb.core.models import Participant, Experimenter

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Assigns users to respective permission group'

    def assign_group(self, lst, group):
        for item in lst:
            item.user.groups = [group]
            item.user.save()
            logger.debug("User %s assigned to %s permissions group.", item.user, group)

    def handle(self, *args, **options):
        participant_list = Participant.objects.select_related('user').exclude(user__email__regex=r'@mailinator.com$')
        experimenter_list = Experimenter.objects.select_related('user').exclude(user__email__regex=r'@mailinator.com$')
        demo_participant_list = Participant.objects.select_related('user').filter(user__email__regex=r'@mailinator.com$')
        demo_experimenter_list = Experimenter.objects.select_related('user').filter(user__email__regex=r'@mailinator.com$')

        self.assign_group(participant_list, Group.objects.get(name="Participants"))
        self.assign_group(demo_participant_list, Group.objects.get(name="Demo Participants"))
        self.assign_group(experimenter_list, Group.objects.get(name="Experimenters"))
        self.assign_group(demo_experimenter_list, Group.objects.get(name="Demo Experimenters"))
