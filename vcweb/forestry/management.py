#from django.dispatch import receiver

from django.db.models.signals import post_save
from vcweb.core import signals
from vcweb.forestry.models import round_setup, round_ended, get_experiment_metadata
from vcweb.core.models import Experiment, ExperimentMetadata

import logging
logger = logging.getLogger(__name__)

#@receiver(signals.round_started, sender='forestry')
def round_started_handler(sender, experiment_id=None, **kwargs):
    logger.debug("forestry handling round started signal")
    round_setup( Experiment.objects.get(pk=experiment_id) )

#@receiver(signals.round_ended, sender='forestry')
def round_ended_handler(sender, experiment_id=None, **kwargs):
    logger.debug("forestry handling round ended signal")
    round_ended(Experiment.objects.get(pk=experiment_id))


def post_save_handler(sender, instance=None, **kwargs):
    if instance.namespace == 'forestry':
        forestry = get_experiment_metadata()
        signals.round_started.connect(round_started_handler, sender=forestry.pk)
        signals.round_ended.connect(round_ended_handler, sender=forestry.pk)

post_save.connect(post_save_handler, sender=ExperimentMetadata)
