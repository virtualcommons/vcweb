from __future__ import print_function
from django.core.management.base import BaseCommand
from vcweb.core.models import User

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Deactivates invalid participants in the subject pool, expects a single file with a list of usernames separated by newlines'

    def add_arguments(self, parser):
        parser.add_argument('--infile', dest='infile', required=True,
                            help='Input file for invalid participants marked from the ASU Web Directory')
        parser.add_argument('--outfile', dest='outfile',
                            required=False,
                            default='deactivated-users.txt',
                            help='Output file for participants marked as invalid from the ASU Web Directory')

    def handle(self, *args, **options):
        input_filename = options['infile']
        output_filename = options['outfile']
        with open(input_filename, 'rb') as infile:
            usernames = []
            for line in infile:
                username = line.strip()
                if username:
                    usernames.append(username)
            logger.debug("Deactivating %s usernames", len(usernames))
        invalid_users = User.objects.filter(username__in=usernames, is_active=True)
        with open(output_filename, 'wb') as outfile:
            print("PK, Username, Date joined, Class status, Email", file=outfile)
            for user in invalid_users:
                print(",".join(map(str, [user.pk, user.username, user.date_joined, user.participant.class_status, user.email])),
                      file=outfile)
        deactivated_users = invalid_users.update(is_active=False)
        logger.debug("Updated %s users", deactivated_users)
