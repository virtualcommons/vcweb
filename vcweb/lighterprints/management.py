from django.dispatch import receiver
from django.db.models.signals import post_syncdb
from vcweb.core.models import ExperimentMetadata
import vcweb
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

@receiver(post_syncdb, sender=vcweb.core.models, dispatch_uid='lighterprints_metadata_creator')
def post_syncdb_handler(sender, **kwargs):
    '''
    creates the forestry ExperimentMetadata record if not already created.
    FIXME: what are pros/cons for doing it this way vs adding it to initial_data.json
    pros:
    1. don't have to hard-code pks and pk references..
    cons:
    1. have to invoke syncdb in order to get this to run
    '''
    experiment_metadata_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "A mobile-ready HTML5 experiment / game that educates and examines how groups of people coordinate to reach carbon emission targets.",
            "namespace": "lighterprints",
            "title": "Lighter Footprints",
            "date_created": datetime.now()
            }
    experiment_metadata, created = ExperimentMetadata.objects.get_or_create(**experiment_metadata_dict)
    logger.debug("experiment metadata: %s (%s)", experiment_metadata, created)


