from django.apps import AppConfig

import logging
import mimetypes

logger = logging.getLogger(__name__)


class VcwebCoreConfig(AppConfig):
    name = 'vcweb.core'
    verbose_name = 'vcweb core management services'

    def ready(self):
        logger.debug("vcweb core ready")
        mimetypes.init()

