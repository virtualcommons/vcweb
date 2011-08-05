#from django.dispatch import receiver

from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata
import vcweb
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

'''
creates the sanitation ExperimentMetadata record if not already created.

pros/cons for doing it this way vs adding it to initial_data.json

pros:
1. don't have to hard-code pks and pk references

cons:
1. have to invoke syncdb in order to get this to run, which is unacceptable once we
start having persistent data

'''

def post_syncdb_handler(sender, **kwargs):
    sanitation_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version sanitation experiment.",
            "namespace": "sanitation",
            "title": "Sanitation Experiment",
            "date_created": datetime.now()
            }
    sanitation_metadata, created = ExperimentMetadata.objects.get_or_create(**sanitation_dict)
    logger.debug("sanitation: %s (%s)", sanitation_metadata, created)

post_syncdb.connect(post_syncdb_handler, sender=vcweb.core.models,
        dispatch_uid='sanitation_metadata_creator')
