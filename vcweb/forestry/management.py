#from django.dispatch import receiver

from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata

import vcweb

import logging
logger = logging.getLogger(__name__)

'''
creates the forestry ExperimentMetadata record if not already created.

is this any better than adding it to directly to initial_data.json?
'''

def post_syncdb_handler(sender, **kwargs):
    forestry_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version of the forestry field experiments.",
            "namespace": "forestry",
            "title": "Forestry Web Experiment",
            "date_created": "2011-01-01"
            }
    logger.debug("forestry: %s (%s)" % ExperimentMetadata.objects.get_or_create(**forestry_dict))

post_syncdb.connect(post_syncdb_handler, sender=vcweb.core.models,
        dispatch_uid='forestry_metadata_creator')


