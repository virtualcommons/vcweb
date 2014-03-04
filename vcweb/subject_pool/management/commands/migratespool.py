from django.core.management.base import BaseCommand, CommandError
from vcweb.core.models import Participant
import mysql.connector

import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrates the legacy subject pool data into the vcweb subject pool'

    def handle(self, *args, **options):
        # open db connection to subject pool
        cnx = mysql.connector.connect(user='spool', password='spool.migration', host='127.0.0.1', database='spool')
        self.stdout.write("opened connection %s to spool database" % cnx)
        cnx.close()
