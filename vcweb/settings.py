from django.contrib import messages
from os import path, makedirs

DEBUG = True
TEMPLATE_DEBUG = DEBUG

USE_TZ = False

SERVER_EMAIL='vcweb@asu.edu'
EMAIL_HOST='smtp.asu.edu'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ADMINS = (
        ('Allen Lee', 'allen.lee@asu.edu')
        )

MANAGERS = ADMINS

DATA_DIR = 'data'

DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': path.join(DATA_DIR, 'vcweb.db')
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

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

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
        'vcweb.core.context_processors.socket_io',
        'vcweb.core.context_processors.debug_mode',
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
        'django.contrib.admin',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'vcweb.core',
        'vcweb.forestry',
        'vcweb.sanitation',
        'vcweb.lighterprints',
        'dajaxice',
        'djcelery',
        'djkombu',
        'raven.contrib.django',
        'kronos',
        'south',
        )

SOUTH_TESTS_MIGRATE = False

DAJAXICE_MEDIA_PREFIX = "dajaxice"

# socket.io configuration
SOCKET_IO_PORT = 8882;

# celerybeat configuration
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERYBEAT_MAX_LOOP_INTERVAL = 5
CELERYBEAT_LOG_FILE = 'celerybeat.log'
CELERYBEAT_LOG_LEVEL = 'ERROR'

# simplest celery transport that uses Django database (djkombu_messages)
BROKER_BACKEND = "djkombu.transport.DatabaseTransport"
# django celery integration
# celery rabbitmq/amqp configuration
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "vcweb"
BROKER_VHOST = "vcweb.vhost"
BROKER_PASSWORD = 'CUSTOMIZE_ME'

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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path.join(STATIC_ROOT, 'media')
 
# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/media/'

# set up jquery-ui css classes for django messages
MESSAGE_TAGS = {
        messages.constants.INFO : 'ui-state-highlight ui-corner-all',
        messages.constants.WARNING: 'ui-state-error ui-corner-all',
        messages.constants.ERROR: 'ui-state-error ui-corner-all'
        }

GRAPH_DATABASE_PATH=path.join(DATA_DIR, 'neo4j-store')

try:
    from settings_local import *
except ImportError:
    pass

LOG_DIRECTORY = 'logs' if DEBUG else '/opt/vcweb/logs'
try:
    makedirs(LOG_DIRECTORY)
except OSError:
    pass

# logging configuration
VCWEB_LOG_FILENAME = 'vcweb.log'
TORNADIO_LOG_FILENAME = 'tornadio.log'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry', 'vcweb.file'],
    },
    'formatters': {
        'verbose': {
             'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'vcweb_verbose': {
            'format': '%(levelname)s %(asctime)s [%(name)s|%(funcName)s:%(lineno)d] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
#        'null': {
#            'level':'DEBUG',
#            'class':'django.utils.log.NullHandler',
#        },
        'sentry': {
             'level': 'ERROR',
             'formatter': 'verbose',
             'class': 'raven.contrib.django.handlers.SentryHandler',
        },
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
            'formatter': 'vcweb_verbose',
        },
        'vcweb.file': {
            'level': 'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'vcweb_verbose',
            'filename': path.join(LOG_DIRECTORY, VCWEB_LOG_FILENAME),
            'backupCount': 6,
            'maxBytes': 10000000,
        },
        'tornadio.file': {
            'level': 'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'vcweb_verbose',
            'filename': path.join(LOG_DIRECTORY, TORNADIO_LOG_FILENAME),
            'backupCount': 6,
            'maxBytes': 10000000,
        },
    },
    'loggers': {
        'django.db.backends': {
            'level':'ERROR',
            'handlers':['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'vcweb': {
            'handlers': ['vcweb.file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'tornadio.vcweb': {
            'handlers': ['tornadio.file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


# this is the last thing to happen so we can override django-celery configuration
# settings
import djcelery
djcelery.setup_loader()

