# Staging server settings
from .base import *
DEBUG = True

ENVIRONMENT = Environment.STAGING

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# XXX: no i18n for the time being
USE_I18N = False

SITE_URL = 'https://dev.vcweb.asu.edu'

# security settings

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

WEBSOCKET_SSL = True
