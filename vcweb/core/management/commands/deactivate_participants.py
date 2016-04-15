from django.core.management.base import BaseCommand
from vcweb.core.models import User

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deactivates invalid participants in the subject pool, expects a single file with a list of usernames separated by newlines'

    def add_arguments(self, parser):
        parser.add_argument('--infile', dest='infile', required=True,
                            help='Input file for invalid participants marked from the ASU Web Directory')

    def handle(self, *args, **options):
        filename = options['infile']
        with open(filename, 'rb') as infile:
            usernames = []
            for line in infile:
                username = line.strip()
                if username:
                    usernames.append(username)
            logger.debug("usernames: %s", usernames)
            inactive_users = User.objects.filter(username__in=usernames).update(is_active=False)
            logger.debug("deactivated %s users", inactive_users.count())
