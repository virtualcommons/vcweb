# Production Django settings for vcweb
from .base import *
DEBUG = False
ENVIRONMENT = Environment.PRODUCTION

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

SITE_URL = 'https://commons.asu.edu'

SUBJECT_POOL_INVITATION_DELAY = 3

# security settings

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
WEBSOCKET_SSL = True
