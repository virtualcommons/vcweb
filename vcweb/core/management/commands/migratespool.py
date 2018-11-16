from datetime import datetime, timedelta
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from vcweb.core.models import Participant, Institution, set_full_name
from vcweb.core.models import OstromlabFaqEntry


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrates the legacy subject pool data into the vcweb subject pool'

    def migrate_participants(self, cnx):
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
        class_status_offsets = {'Freshman': timedelta(
            days=365 * 3), 'Sophomore': timedelta(days=365 * 2), 'Junior': timedelta(days=365)}
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
                    self.stdout.write(
                        "Skipping {} that registered on {}".format(class_status, date_created))
                    skipped_participants.append("%s %s" % (username, email))
            try:
                u = User.objects.get(email=email)
                self.stdout.write("user already exists: {}".format(u))
                set_full_name(u, full_name)
                existing_users.append(u)
            except User.DoesNotExist:
                u = User(username=username, email=email,
                         password=User.objects.make_random_password())
                new_users.append(u)
                set_full_name(u, full_name)
            u.save()
            try:
                p = Participant.objects.get(user=u)
                self.stdout.write("Participant %s already exists" % p)
            except Participant.DoesNotExist:
                p = Participant(user=u)
            if not p.major:
                p.major = major
            if not p.gender:
                p.gender = gender
            if not p.class_status:
                p.class_status = class_status
            p.date_created = date_created
            p.can_receive_invitations = True
            p.institution = asu_institution
            if p.pk:
                self.stdout.write("Updating existing participant {}".format(p))
                p.save()
            else:
                self.stdout.write("Creating participant {} major: {} gender: {} class_status {} institution {}".format(
                    p, p.major, p.gender, p.class_status, asu_institution))
                new_participants.append(p)
            if p.user is None or not p.user.pk:
                self.stdout.write(
                    "XXX: participant %s with user %s, %s" % (p, p.user, p.user.pk))
        # User.objects.bulk_create(new_users)
        Participant.objects.bulk_create(new_participants)
        self.stdout.write("existing users: %s" % existing_users)
        self.stdout.write("skipped users: %s" % skipped_participants)

    def migrate_faq(self, cnx):
        cursor = cnx.cursor()
        cursor.execute("SELECT question, answer FROM faq_entry")
        contributor = User.objects.get(pk=1)
        for (question, answer) in cursor:
            faq_entry, created = OstromlabFaqEntry.objects.get_or_create(
                question=question, answer=answer, contributor=contributor)
            self.stdout.write("faq entry %s (%s)" % (faq_entry, created))

    def handle(self, *args, **options):
        import mysql.connector
        # open db connection to subject pool
        cnx = mysql.connector.connect(
            user='spool', password='spool.migration', host='127.0.0.1', database='spool')
        self.stdout.write("opened connection %s to spool database" % cnx)
        self.migrate_participants(cnx)
        self.migrate_faq(cnx)
        cnx.close()
