from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class VcwebCoreConfig(AppConfig):
    name = 'vcweb.core'
    verbose_name = 'vcweb core management services'

    def ready(self):
        logger.debug("vcweb core ready")
