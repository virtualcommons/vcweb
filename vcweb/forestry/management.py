#from django.dispatch import receiver

from django.db.models.signals import post_syncdb
from vcweb.core import signals
from vcweb.forestry.models import round_setup, round_ended
from vcweb.core.models import Experiment, ExperimentMetadata

import vcweb.core.models

import logging
logger = logging.getLogger(__name__)

'''
    {
        "fields": {
            "about_url": "http://commons.asu.edu", 
            "description": "Web-based version of the forestry field experiments.", 
            "namespace": "forestry", 
            "title": "Forestry Web Experiment",
            "date_created": "2011-01-01"
        }, 
        "model": "core.experimentmetadata", 
        "pk": 1
    }, 

'''

#@receiver(signals.round_started, sender='forestry')
def round_started_handler(sender, experiment_id=None, **kwargs):
    logger.debug("forestry handling round started signal")
    round_setup( Experiment.objects.get(pk=experiment_id) )

#@receiver(signals.round_ended, sender='forestry')
def round_ended_handler(sender, experiment_id=None, **kwargs):
    logger.debug("forestry handling round ended signal")
    round_ended(Experiment.objects.get(pk=experiment_id))


def post_syncdb_handler(sender, **kwargs):
    forestry_dict = {
            "about_url": "http://commons.asu.edu",
            "description": "Web-based version of the forestry field experiments.",
            "namespace": "forestry",
            "title": "Forestry Web Experiment",
            "date_created": "2011-01-01"
            }
    forestry, created = ExperimentMetadata.objects.get_or_create(**forestry_dict)
    if created:
        signals.round_started.connect(round_started_handler, sender=forestry.pk)
        signals.round_ended.connect(round_ended_handler, sender=forestry.pk)
    else:
        logger.debug("There was an existing forestry ExperimentMetadata experiment")

post_syncdb.connect(post_syncdb_handler, sender=vcweb.core.models)
