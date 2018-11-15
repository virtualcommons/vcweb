# Production Django settings for vcweb
from .base import *
DEBUG = False
ENVIRONMENT = Environment.PRODUCTION

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

SITE_URL = 'https://commons.asu.edu'

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
WEBSOCKET_SSL = True
