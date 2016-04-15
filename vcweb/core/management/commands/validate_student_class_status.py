from django.core.management.base import BaseCommand
from django.conf import settings
from vcweb.core.models import Participant, ASUWebDirectoryProfile, create_markdown_email

import unicodecsv as csv
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validates ASU Participant class statuses for the subject pool'

    def add_arguments(self, parser):
        parser.add_argument('--output', dest='output', default='/tmp/invalid-students.csv',
                            help='Output file for participant status data culled from the ASU Web Directory')

    def handle(self, *args, **options):
        active_participants = Participant.objects.active(institution__name='Arizona State University')
        filename = options['output']
        invalid_participants = []
        for participant in active_participants:
            # naive check to see if the participant's username has been set to their ASURITE
            if participant.email != participant.username:
                directory_profile = ASUWebDirectoryProfile(participant.username)
                if directory_profile.profile_data is None or not directory_profile.is_undergraduate:
                    invalid_participants.append(participant)
        with open(filename, 'wb') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(['PK', 'Username', 'Email', 'Date Joined', 'Class Status'])
            for participant in invalid_participants:
                writer.writerow([participant.pk, participant.username, participant.email,
                                 participant.user.date_joined.strftime("%m-%d-%Y %H:%M"),
                                 participant.class_status])
        logger.debug("Checked permissions for %s participants", active_participants.count())
        email = create_markdown_email(template="email/monthly-audit-email.txt",
                                      context={'participants': invalid_participants},
                                      subject="VCWEB Monthly Audit", to_email=[settings.DEFAULT_EMAIL])
        email.send()
