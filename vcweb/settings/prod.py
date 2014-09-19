# Production Django settings for vcweb
from .base import *
DEBUG = False
TEMPLATE_DEBUG = DEBUG

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

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
    'dsn': 'https://public:secret@vcweb.asu.edu/1',
}

SITE_URL = 'https://vcweb.asu.edu'
