from django.dispatch import receiver
from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata
import vcweb
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

@receiver(post_syncdb, sender=vcweb.core.models, dispatch_uid='lighterprints_metadata_creator')
def post_syncdb_handler(sender, **kwargs):
    experiment_metadata_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "A mobile-ready HTML5 experiment / game that educates and examines how groups of people coordinate to reach carbon emission targets.",
            "namespace": "lighterprints",
            "title": "Lighter Footprints",
            "date_created": "2011-01-01"
            }
    created = False
    try:
        metadata = ExperimentMetadata.objects.get(namespace='lighterprints')
    except:
        metadata, created = ExperimentMetadata.objects.get_or_create(**experiment_metadata_dict)
    logger.debug("experiment metadata: %s (%s)", metadata, created)


