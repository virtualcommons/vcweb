from django.core.management.base import BaseCommand
from django.conf import settings
from .models import Participant, ASUWebDirectoryProfile, create_markdown_email

import unicodecsv as csv
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validates ASU Participant class statuses for the subject pool'

    def handle(self, *args, **options):
        participants = Participant.objects.select_related('user').filter(institution__name='Arizona State University')
        invalid_participants = []

        filename = '/tmp/invalid_students.csv'
        with open(filename, 'wb') as csvfile:
            writer = csv.writer(csvfile, delimiter=',')
            writer.writerow(['PK', 'Username', 'Email', 'Date Joined', 'Class Status'])

            logger.debug("Checking permissions for total %s participants", participants.count())

            for participant in participants:
                if participant.email != participant.username:
                    directory_profile = ASUWebDirectoryProfile(participant.username)
                    if directory_profile.profile_data is None or not directory_profile.is_undergraduate:
                        invalid_participants.append(participant)
                        writer.writerow([participant.pk, participant.username, participant.email,
                                         participant.user.date_joined.strftime("%m-%d-%Y %H:%M"),
                                         participant.class_status])

        email = create_markdown_email(template="email/monthly-audit-email.txt",
                                      context={'participants': invalid_participants},
                                      subject="VCWEB Monthly Audit", to_email=[settings.DEFAULT_EMAIL])
        email.send()
