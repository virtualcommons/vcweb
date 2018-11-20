import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ExperimentAppConfig(AppConfig):
    name = 'vcweb.experiment.bound'
    verbose_name = 'Boundary Effects Experiment App'

    def ready(self):
        logger.debug("boundary effects experiment app ready")
