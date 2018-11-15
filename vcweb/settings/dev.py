# local development Django settings for vcweb
from .base import *
DEBUG = not ENVIRONMENT.is_production

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE

# XXX: no i18n for the time being
USE_I18N = False

SITE_URL = 'https://dev.vcweb.asu.edu'

INSTALLED_APPS += (
    'debug_toolbar',
    'sslserver',
)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

WEBSOCKET_SSL = True
