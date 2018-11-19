from django.apps import AppConfig

import logging

logger = logging.getLogger(__name__)


class SubjectPoolConfig(AppConfig):
    name = 'vcweb.core.subjectpool'
    verbose_name = 'Subject Pool Management Services'

    def ready(self):
        logger.debug("Subject pool app initialized")
