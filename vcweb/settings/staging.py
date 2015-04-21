# Local Development Django settings for vcweb
from .base import *
DEBUG = True

ENVIRONMENT = Environment.STAGING

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vcweb',
        'USER': 'vcweb',
        'PASSWORD': 'CUSTOMIZE_ME',
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# XXX: no i18n for the time being
USE_I18N = False

SITE_URL = 'https://vcweb-dev.asu.edu'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'customize this secret key'
WEBSOCKET_SSL = True
