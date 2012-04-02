from django.db.models import signals
from django.dispatch import receiver
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

@receiver(signals.post_syncdb, sender=vcweb.core.models, dispatch_uid='sanitation_metadata_creator')
def post_syncdb_handler(sender, **kwargs):
    sanitation_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version sanitation experiment.",
            "namespace": "sanitation",
            "title": "Sanitation Experiment",
            "date_created": datetime.now()
            }
    try:
        ExperimentMetadata.objects.get(namespace='sanitation')
    except:
        ExperimentMetadata.objects.create(**sanitation_dict)
