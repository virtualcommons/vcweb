from django.core.management.base import BaseCommand
import unicodecsv
import logging

from vcweb.core.models import ExperimentMetadata, ParticipantSignup
from vcweb.core.subjectpool.models import generate_participant_report


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Generates a CSV with all ParticipantSignups for the given ExperimentMetadata'''

    def add_arguments(self, parser):
        parser.add_argument('--experiment-metadata-pk', dest='experiment_metadata_pk', required=True,
                            help='ExperimentMetadata PK used to filter ParticipantSignups')
        parser.add_argument('--outfile', dest='outfile',
                            required=False,
                            default='experiment-participants.txt',
                            help='CSV with all ParticipantSignups for the given ExperimentMetadata')

    def handle(self, *args, **options):
        experiment_metadata_pk = options['experiment_metadata_pk']
        experiment_metadata = ExperimentMetadata.objects.get(pk=experiment_metadata_pk)
        output_filename = options['outfile']
        with open(output_filename, 'wb') as outfile:
            writer = unicodecsv.writer(outfile, encoding='utf-8')
            generate_participant_report(writer, experiment_metadata,
                                        attendance=ParticipantSignup.ATTENDANCE.participated)
