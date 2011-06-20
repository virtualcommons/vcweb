from django.db.models import signals
from django.dispatch import receiver
from vcweb.core.models import ExperimentMetadata

import vcweb

import logging
logger = logging.getLogger(__name__)

'''
creates the forestry ExperimentMetadata record if not already created.

XXX: also create forestry parameters here?

FIXME: what are pros/cons for doing it this way vs adding it to initial_data.json
pros:
1. don't have to hard-code pks and pk references..

cons:
1. have to invoke syncdb in order to get this to run

'''

@receiver(signals.post_syncdb, sender=vcweb.core.models, dispatch_uid='forestry_metadata_creator')
def post_syncdb_handler(sender, **kwargs):
    forestry_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "A web-based version of forestry field experiments (Cardenas, Janssen and Bousquet).",
            "namespace": "forestry",
            "title": "Forestry Experiment",
            "date_created": "2011-01-01"
            }
    forestry_metadata, created = ExperimentMetadata.objects.get_or_create(**forestry_dict)
    logger.debug("forestry: %s (%s)" % (forestry_metadata, created))
