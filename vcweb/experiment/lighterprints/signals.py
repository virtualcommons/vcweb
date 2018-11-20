import logging

from django.db import transaction
from django.dispatch import receiver

from vcweb.core import signals
from .models import (EXPERIMENT_METADATA_NAME, get_experiment_completed_parameter,
                     get_footprint_level_parameter, is_level_based_experiment)
from .services import daily_update

logger = logging.getLogger(__name__)


@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME, dispatch_uid=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_ended_handler(sender, experiment=None, **kwargs):
    logger.debug("ending lighter footprints round %s, sending summary emails", experiment)
    daily_update(experiment)


@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME, dispatch_uid=EXPERIMENT_METADATA_NAME)
@transaction.atomic
def round_started_handler(sender, experiment=None, **kwargs):
    logger.debug("starting lighter footprints round %s", experiment)
    round_data = experiment.current_round_data
    # FIXME: experiment.initialize_parameters could do some of this except for
    # setting the default values properly
    experiment_completed_parameter = get_experiment_completed_parameter()
    initial_group_parameters = [experiment_completed_parameter]
    initial_parameter_defaults = {experiment_completed_parameter: False}
    if is_level_based_experiment(experiment):
        footprint_level_parameter = get_footprint_level_parameter()
        initial_group_parameters.append(footprint_level_parameter)
        initial_parameter_defaults[footprint_level_parameter] = 1
    experiment.initialize_data_values(
        group_parameters=initial_group_parameters,
        round_data=round_data,
        defaults=initial_parameter_defaults,
    )
