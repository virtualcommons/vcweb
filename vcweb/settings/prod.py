# Production Django settings for vcweb
from .base import *
DEBUG = False
ENVIRONMENT = Environment.PRODUCTION

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'localhost',
        'NAME': 'vcweb',
        'USER': 'vcweb',
        'PASSWORD': 'CUSTOMIZE_ME',
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'CUSTOMIZE_ME'

RAVEN_CONFIG = {
    'dsn': 'https://public:secret@sentry.commons.asu.edu/1',
}

SITE_URL = 'https://vcweb.asu.edu'

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
WEBSOCKET_SSL = True
