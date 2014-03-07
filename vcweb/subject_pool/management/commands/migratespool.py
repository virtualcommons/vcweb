from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from vcweb.core.models import Participant, Institution, set_full_name
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
                " WHERE u.active=1")
        cursor.execute(query)
        asu_institution = Institution.objects.get(name='Arizona State University')
        users = []
        participants = []
        for (username, full_name, date_created, email, gender, class_status, major, affiliation) in cursor:
            u = User(username=username, email=email, password=User.objects.make_random_password())
            set_full_name(u, full_name)
            users.append(u)
            p = Participant(user=u, can_receive_invitations=True, gender=gender, major=major,
                    class_status=class_status, date_created=date_created, institution=asu_institution)
            self.stdout.write(u"processing {} {} {}, created {}".format(full_name, username, email, p))
            participants.append(p)
        self.stdout.write("participants: {} with users: {}".format(len(participants), len(users)))
        cnx.close()
