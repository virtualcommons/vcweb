from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class ExperimentAppConfig(AppConfig):
    name = 'vcweb.experiment.bound'
    verbose_name = 'Boundary Effects Experiment App'

    def ready(self):
        from .signals import round_started_handler, round_ended_handler
        logger.debug("boundary effects experiment app ready")
