from datetime import date
from collections import defaultdict
import logging
import itertools

from django.core.management.base import BaseCommand

from vcweb.core.models import ParticipantExperimentRelationship, ParticipantGroupRelationship, Participant


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fixes dupe users/participants with identical emails created, see https://bitbucket.org/virtualcommons/vcweb/issue/201'

    def is_legitimate(self, p):
        if p.username == p.email:
            return False
        elif p.full_name is None or not p.full_name:
            return False
        return True

    def handle(self, *args, **options):
        """ FIXME: grossly inefficient, but not expected to run very often """
        """ identify all dupe users/participants with identical emails """
        # maps legitimate participants to a list of their duplicated
        # participants
        duplicate_participants = defaultdict(list)
        for p in Participant.objects.filter(date_created__gt=date(2014, 4, 13)):
            doppelgangers = Participant.objects.filter(user__email=p.email)
            if doppelgangers.count() > 1:
                # pick the 'legitimate' as the one where the username is
                # non-null and != the email
                legitimate = p
                for d in doppelgangers:
                    if self.is_legitimate(d):
                        legitimate = d
                for d in doppelgangers:
                    if d != legitimate:
                        duplicate_participants[legitimate].append(d)

        logger.debug("duplicate participants: %s", duplicate_participants)
# fix ParticipantExperimentRelationship and ParticipantGroupRelationship
        for canonical, dupes in list(duplicate_participants.items()):
            pers = ParticipantExperimentRelationship.objects.filter(
                participant__in=dupes)
            logger.debug(
                "updating dupes %s -> canonical version: %s", dupes, canonical)
            num_updated = pers.update(participant=canonical)
            logger.debug("pers: %s, updated %s", pers, num_updated)
            pgrs = ParticipantGroupRelationship.objects.filter(
                participant__in=dupes)
            num_updated = pgrs.update(participant=canonical)
            logger.debug("pgrs: %s, updated %s", pgrs, num_updated)

        dupe_pks = [dupe.pk for dupe in itertools.chain(
            *list(duplicate_participants.values()))]
        Participant.objects.filter(pk__in=dupe_pks).delete()
