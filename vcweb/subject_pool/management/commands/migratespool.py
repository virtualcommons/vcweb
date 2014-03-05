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
        cursor = cnx.cursor()
        query = ("SELECT u.username, u.fullName, u.dateCreated, u.emailAddress, p.gender, p.classStatus, p.major, p.affiliation "
                " FROM user u inner join participant p on u.id=p.id "
                " WHERE u.active=1 LIMIT 10")
        cursor.execute(query)
        for (username, full_name, date_created, email, gender, class_status, major, affiliation) in cursor:
            self.stdout.write("processing {} {}".format(username, email))
        cnx.close()
