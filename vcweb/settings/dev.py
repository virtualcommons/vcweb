# Local Development Django settings for vcweb
from .base import *
DEBUG = not ENVIRONMENT.is_production

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vcweb',
        'USER': 'vcweb',
        'PASSWORD': 'CUSTOMIZE_ME',
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# XXX: no i18n for the time being
USE_I18N = False

SITE_URL = 'https://vcweb-dev.asu.edu'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'customize this dev secret key'

INSTALLED_APPS += (
    'debug_toolbar.apps.DebugToolbarConfig',
    'sslserver',
)
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

WEBSOCKET_SSL = True
