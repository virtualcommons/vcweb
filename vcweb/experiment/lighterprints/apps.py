from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class LighterprintsConfig(AppConfig):
    name = 'vcweb.experiment.lighterprints'
    verbose_name = 'Lighter Footprints'

    def ready(self):
        from .signals import round_started_handler, round_ended_handler
        logger.debug("lighterprints app ready")
