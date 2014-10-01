import os
import logging

DEBUG = True
TEMPLATE_DEBUG = DEBUG

USE_TZ = False

SITE_URL = 'http://localhost:8000'

BASE_DIR = os.path.dirname(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

DEMO_EXPERIMENTER_EMAIL = 'vcweb.demo@mailinator.com'
DEFAULT_FROM_EMAIL = 'vcweb@asu.edu'
SERVER_EMAIL = 'vcweb@asu.edu'
SERVER_NAME = 'vcweb.asu.edu'
EMAIL_HOST = 'smtp.asu.edu'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ALLOWED_HOSTS = ('.asu.edu', 'localhost',)
ADMINS = (
    ('Allen Lee', 'allen.lee@asu.edu'),
)
MANAGERS = ADMINS

DATA_DIR = 'data'
GRAPH_DATABASE_PATH = os.path.join(DATA_DIR, 'neo4j')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'vcweb.db'),
    },
    'postgres': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vcweb',
        'USER': 'vcweb',
        'PASSWORD': '',
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
USE_I18N = False

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.  Default is '/static/admin/'
# ADMIN_MEDIA_PREFIX = '/static/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '2km^iq&48&6uv*x$ew@56d0#w9zqth@)_4tby(85+ac2wf4r-u'

CSRF_FAILURE_VIEW = 'vcweb.core.views.csrf_failure'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    "django.core.context_processors.debug",
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    "django.core.context_processors.tz",
    'django.contrib.messages.context_processors.messages',
    'vcweb.core.context_processors.common',
    'dealer.contrib.django.context_processor',
)

MIDDLEWARE_CLASSES = (
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cas.middleware.CASMiddleware',
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

DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

THIRD_PARTY_APPS = (
    'autocomplete_light',
    'raven.contrib.django.raven_compat',
    'contact_form',
    'kronos',
    'django_extensions',
    'mptt',
    'bootstrap3',
    'cas',
)


VCWEB_EXPERIMENTS = (
    'vcweb.experiment.forestry',
    'vcweb.experiment.lighterprints',
    'vcweb.experiment.bound',
    'vcweb.experiment.broker',
    'vcweb.experiment.irrigation',
)

VCWEB_APPS = ('vcweb.core',) + VCWEB_EXPERIMENTS


INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + VCWEB_APPS

LOGIN_REDIRECT_URL = '/dashboard'

# websockets configuration
WEBSOCKET_PORT = 8882
WEBSOCKET_URI = '/websocket'

# activation window
ACCOUNT_ACTIVATION_DAYS = 30


# use email as username for authentication
AUTHENTICATION_BACKENDS = (
    'cas.backends.CASBackend',
    "vcweb.core.backends.EmailAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/vcweb/static/'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'vcweb', 'static').replace('\\', '/'),)

#### Media file configuration (for user uploads etc) ####

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(STATIC_ROOT, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/media/'


def is_accessible(directory_path):
    return os.path.isdir(directory_path) and os.access(directory_path, os.W_OK | os.X_OK)

LOG_DIRECTORY = '/opt/vcweb/logs'

if not is_accessible(LOG_DIRECTORY):
    try:
        os.makedirs(LOG_DIRECTORY)
    except OSError:
        print "Unable to create absolute log directory at %s, setting to relative path logs instead" % LOG_DIRECTORY
        LOG_DIRECTORY = 'logs'
        if not is_accessible(LOG_DIRECTORY):
            try:
                os.makedirs(LOG_DIRECTORY)
            except OSError:
                print "Couldn't create any log directory, startup will fail"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry', 'vcweb.file'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s [%(name)s|%(funcName)s:%(lineno)d] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'formatter': 'verbose',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'vcweb.file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIRECTORY, 'vcweb.log'),
            'backupCount': 6,
            'maxBytes': 10000000,
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
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
            'level': 'DEBUG',
            'handlers': ['vcweb.file', 'console'],
            'propagate': False,
        },
    }
}

# Required if using CAS
CAS_UNIVERSITY_NAME = "Arizona State University"
CAS_UNIVERSITY_URL = "http://www.asu.edu"
WEB_DIRECTORY_URL = "https://webapp4.asu.edu/directory/ws/search?asuriteId="

# Required settings for CAS Library
CAS_SERVER_URL = "https://weblogin.asu.edu/cas/"
CAS_IGNORE_REFERER = True
# CAS_LOGOUT_COMPLETELY = True
# CAS_PROVIDE_URL_TO_LOGOUT = True
CAS_REDIRECT_URL = "/cas/asu"
CAS_AUTOCREATE_USERS = False
CAS_RESPONSE_CALLBACKS = (
    'vcweb.core.views.get_cas_user',
)
CAS_CUSTOM_FORBIDDEN = 'cas_error'

# reset in local.py to enable more verbose logging (e.g.,
# DISABLED_TEST_LOGLEVEL = logging.NOTSET)
DISABLED_TEST_LOGLEVEL = logging.WARNING

TEST_RUNNER = 'vcweb.core.tests.runner.VcwebTestRunner'

# revision reporting support using dealer
DEALER_TYPE = 'git'
DEALER_SILENT = True
DEALER_BACKENDS = ('git', 'mercurial')
DEALER_PATH = BASE_DIR
