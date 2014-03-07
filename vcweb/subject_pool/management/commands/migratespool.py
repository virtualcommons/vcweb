from datetime import datetime, timedelta
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
        existing_users = []
        new_users = []
        new_participants = []
        skipped_participants = []
        class_status_offsets = {'Freshman': timedelta(days=365*3), 'Sophomore': timedelta(days=365*2), 'Junior': timedelta(days=365)}
        now = datetime.now()
        for (username, full_name, date_created, email, gender, class_status, major, affiliation) in cursor:
            if class_status == 'Senior':
                self.stdout.write("skipping seniors {}".format(email))
                skipped_participants.append("%s %s" % (username, email))
                continue
            else:
                self.stdout.write("checking delta for class %s" % class_status)
                delta = class_status_offsets[class_status]
                if date_created + delta < now:
                    # this one is expired
                    self.stdout.write("Skipping {} that registered on {}".format(class_status, date_created))
                    skipped_participants.append("%s %s" % (username, email))
            #self.stdout.write(u"Looking at {} {} class {}".format(username, email, class_status))
            try:
                u = User.objects.get(email=email)
                self.stdout.write(u"user already exists: {}".format(u))
                existing_users.append(u)
            except User.DoesNotExist:
                u = User(username=username, email=email, password=User.objects.make_random_password())
                new_users.append(u)
                set_full_name(u, full_name)
                p = Participant(user=u, can_receive_invitations=True, gender=gender, major=major,
                        class_status=class_status, date_created=date_created, institution=asu_institution)
                self.stdout.write(u"processing {} {} {}, created {}".format(full_name, username, email, p))
                new_participants.append(p)
        User.objects.bulk_create(new_users)
        Participant.objects.bulk_create(new_participants)
        self.stdout.write("new participants: {}, existing users: {}".format(len(new_participants), len(existing_users)))
        self.stdout.write("existing users: %s" % existing_users)
        self.stdout.write("skipped users: %s" % skipped_participants)
        cnx.close()
