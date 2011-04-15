# Django settings for vcweb project.
from os import path
import logging

LOG_FILENAME = 'vcweb.log'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'medium': {
            'format': '%(asctime)s %(levelname)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level':'DEBUG',
            'class':'django.utils.log.NullHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'medium',
            'filename': LOG_FILENAME,
        },
    },
    'loggers': {
        'django': {
            'handlers':['null'],
            'propagate': True,
            'level':'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'vcweb': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        }
    }
}

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
        ('Allen Lee', 'allen.lee@asu.edu')
        # ('Your Name', 'your_email@domain.com'),
        )

MANAGERS = ADMINS

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'vcweb.db',
            }
        }
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Phoenix'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
#MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
#MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.  Default is '/static/admin/'
# ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '2km^iq&48&6uv*x$ew@56d0#w9zqth@)_4tby(85+ac2wf4r-u'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
        'django.template.loaders.eggs.Loader',
        )

TEMPLATE_CONTEXT_PROCESSORS = (
        'django.core.context_processors.request',
        'django.core.context_processors.static',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
        )

MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'vcweb.core.middleware.ExceptionHandlingMiddleware',
        )

ROOT_URLCONF = 'vcweb.urls'

# cookie storage vs session storage of django messages
#MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

TEMPLATE_DIRS = (
        # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
        )

INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.admin',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'vcweb.core',
        'vcweb.forestry',
        'djcelery',
        'djkombu',
        'dajaxice',
        )


DAJAXICE_MEDIA_PREFIX = "dajaxice"

EMAIL_HOST = "smtp.asu.edu"

# celery rabbitmq/amqp configuration
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "vcweb"
BROKER_PASSWORD = 'override this in settings_local.py'
BROKER_VHOST = "vcweb.vhost"

# celerybeat configuration
CELERYBEAT_MAX_LOOP_INTERVAL = 5
CELERYBEAT_LOG_FILE = 'celerybeat.log'
CELERYBEAT_LOG_LEVEL = 'ERROR'


# activation window
ACCOUNT_ACTIVATION_DAYS = 30

DEFAULT_FROM_EMAIL = 'commons@asu.edu'

# use email as username for authentication
AUTHENTICATION_BACKENDS = ("vcweb.core.auth.AuthenticationBackend", "django.contrib.auth.backends.ModelBackend",)

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/vcweb/static/'
STATICFILES_DIRS = (
        path.join(path.abspath(path.dirname(__file__)), 'static').replace('\\', '/'),
        )

import djcelery
djcelery.setup_loader()


# set up jquery-ui css classes for django messages
from django.contrib import messages
MESSAGE_TAGS = {
        messages.constants.INFO : 'ui-state-highlight ui-corner-all',
        messages.constants.WARNING: 'ui-state-error ui-corner-all',
        messages.constants.ERROR: 'ui-state-error ui-corner-all'
        }
try:
    from settings_local import *
except ImportError:
    logging.debug("Couldn't load local settings")
    pass


