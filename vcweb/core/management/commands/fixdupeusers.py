from collections import defaultdict
import logging
import itertools

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fixes dupe users/participants with identical emails created, see https://bitbucket.org/virtualcommons/vcweb/issue/201'

    def is_legitimate(self, p):
        if p.username == p.email:
            return False
        elif p.get_full_name() is None or not p.get_full_name():
            return False
        return True

    def handle(self, *args, **options):
        """ FIXME: grossly inefficient, but not expected to run very often """
        """ identify all dupe users/participants with identical emails """
        # maps legitimate participants to a list of their duplicated
        # participants
        duplicate_users = defaultdict(list)
        for u in User.objects.filter(first_name='', email__contains='asu.edu'):
            doppelgangers = User.objects.filter(email=u.email)
            if doppelgangers.count() > 1:
                # pick the 'legitimate' as the one where the username is
                # non-null and != the email
                legitimate = u
                for d in doppelgangers:
                    if self.is_legitimate(d):
                        legitimate = d
                for d in doppelgangers:
                    if d != legitimate:
                        duplicate_users[legitimate].append(d)

        logger.debug(
            "%d: duplicate users: %s", len(duplicate_users), duplicate_users)
# fix ParticipantExperimentRelationship and ParticipantGroupRelationship
        dupe_pks = [
            dupe.pk for dupe in itertools.chain(*list(duplicate_users.values()))]
        User.objects.filter(pk__in=dupe_pks).delete()
