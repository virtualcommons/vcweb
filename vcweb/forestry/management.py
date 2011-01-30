#from django.dispatch import receiver

from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata

import vcweb

import logging
logger = logging.getLogger(__name__)

'''
creates the forestry ExperimentMetadata record if not already created and
registers round_started and round_ended signal handlers
'''

def post_syncdb_handler(sender, **kwargs):
    forestry_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version of the forestry field experiments.",
            "namespace": "forestry",
            "title": "Forestry Web Experiment",
            "date_created": "2011-01-01"
            }
    forestry, created = ExperimentMetadata.objects.get_or_create(**forestry_dict)
    if not created:
        logger.debug("existing forestry ExperimentMetadata experiment")

post_syncdb.connect(post_syncdb_handler, sender=vcweb.core.models,
        dispatch_uid='forestry_metadata_creator')


