#from django.dispatch import receiver

from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata

import vcweb

import logging
logger = logging.getLogger(__name__)

'''
creates the forestry ExperimentMetadata record if not already created.

XXX: also create forestry parameters here?

FIXME: what are pros/cons for doing it this way vs adding it to initial_data.json
pro: don't have to hard-code pks and pk references..
'''

def post_syncdb_handler(sender, **kwargs):
    forestry_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version of the forestry field experiments.",
            "namespace": "forestry",
            "title": "Forestry Web Experiment",
            "date_created": "2011-01-01"
            }
    forestry_metadata, created = ExperimentMetadata.objects.get_or_create(**forestry_dict)
    logger.debug("forestry: %s (%s)" % (forestry_metadata, created))

post_syncdb.connect(post_syncdb_handler, sender=vcweb.core.models,
        dispatch_uid='forestry_metadata_creator')


