from django.core.management.base import BaseCommand
import csv
import logging

from vcweb.core.models import Participant


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Filters existing users from potential set of ASU undergraduate subjects. Expects a csv file with
    First Name, Last Name, ASU Email, Regular Email, ASURITE ID as the header and corresponding data values and
    generates an output.txt file suitable for import into ASU's AMDF facility'''
    args = '<csv-file-with-emails-and-asurite-ids-to-process>'

    def add_arguments(self, parser):
        parser.add_argument('filename',
                            help='CSV file with "First Name, Last Name, ASU Email, Regular Email, ASURITE ID" header"',
                            default='freshman.csv',
                            )

    def handle(self, *args, **options):
        input_filename = options['filename']
        with open(input_filename, 'rt', encoding='utf-8-sig') as infile, open('spool-amdf.txt', 'wt') as outfile, open('spool-dupes.txt', 'wt') as dupes:
            r = csv.reader(infile, dialect=csv.excel)
            header = tuple(next(r))
            # FIXME: make this more broadly generalizable if needed
            print(("header: %s", header))
            assert header == ("First Name", "Last Name", "Asu Email Addr", "Email Addr", "Asu Asurite Id")
            for row in r:
                (first_name, last_name, asu_email, regular_email, asurite) = row
                if Participant.objects.filter(user__username=asurite).exists():
                    dupes.write("%s\n" % row)
                else:
                    outfile.write("%s *%s %s\n" % (asu_email, first_name, last_name))
