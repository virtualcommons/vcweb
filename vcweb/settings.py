import os
from os import path
import locale

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

DEBUG = True
TEMPLATE_DEBUG = DEBUG

USE_TZ = False
SITE_URL = 'https://vcweb.asu.edu'

SETTINGS_PATH = path.abspath(path.dirname(__file__))
SERVER_EMAIL = 'vcweb@asu.edu'
SERVER_NAME = 'vcweb.asu.edu'
EMAIL_HOST = 'smtp.asu.edu'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ALLOWED_HOSTS = ('.asu.edu', 'localhost',)
ADMINS = (
    ('Allen Lee', 'allen.lee@asu.edu')
)

MANAGERS = ADMINS

DATA_DIR = 'data'

GRAPH_DATABASE_PATH = path.join(DATA_DIR, 'neo4j-store')

BITBUCKET_API_USER = 'vcweb'
BITBUCKET_API_PW = 'not quite the real password'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': path.join(DATA_DIR, 'vcweb.db'),
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
    'vcweb.core.context_processors.websocket',
    'vcweb.core.context_processors.debug_mode',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'vcweb.core.middleware.ExceptionHandlingMiddleware',
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

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'autocomplete_light',
    'vcweb.core',
    'vcweb.experiment.forestry',
    'vcweb.experiment.lighterprints',
    'vcweb.experiment.bound',
    'vcweb.experiment.broker',
    #        'vcweb.sanitation',
    'raven.contrib.django',
    'kronos',
    'south',
    'django_extensions',
    'mptt',
    'bootstrap3',
    'cas',
)

SOUTH_TESTS_MIGRATE = False

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# django social auth keys
TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''
FACEBOOK_APP_ID = ''
FACEBOOK_API_SECRET = ''
FACEBOOK_EXTENDED_PERMISSIONS = ['email']
LINKEDIN_CONSUMER_KEY = ''
LINKEDIN_CONSUMER_SECRET = ''
GOOGLE_CONSUMER_KEY = ''
GOOGLE_CONSUMER_SECRET = ''
GOOGLE_OAUTH2_CLIENT_ID = ''
GOOGLE_OAUTH2_CLIENT_SECRET = ''
FOURSQUARE_CONSUMER_KEY = ''
FOURSQUARE_CONSUMER_SECRET = ''
FOURSQUARE_OAUTH_ENDPOINT = 'https://foursquare.com/oauth2/authenticate'
FOURSQUARE_OAUTH_ACCESS_TOKEN_ENDPOINT = 'https://foursquare.com/oauth2/access_token'
FOURSQUARE_VENUE_SEARCH_ENDPOINT = 'https://api.foursquare.com/v2/venues/search'
FOURSQUARE_CATEGORIES_ENDPOINT = 'https://api.foursquare.com/v2/venues/categories'
FOURSQUARE_CONSUMER_DATE_VERIFIED = '20120417'
GITHUB_APP_ID = ''
GITHUB_API_SECRET = ''
DROPBOX_APP_ID = ''
DROPBOX_API_SECRET = ''
FLICKR_APP_ID = ''
FLICKR_API_SECRET = ''
INSTAGRAM_CLIENT_ID = ''
INSTAGRAM_CLIENT_SECRET = ''

LOGIN_REDIRECT_URL = '/dashboard'
LOGIN_ERROR_URL = '/login-error/'
#LOGIN_REDIRECT_URL='/dashboard'
#LOGIN_ERROR_URL='/accounts/login/error'
SOCIAL_AUTH_COMPLETE_URL_NAME = 'socialauth_complete'
SOCIAL_AUTH_ASSOCIATE_URL_NAME = 'socialauth_associate_complete'

SOCIAL_AUTH_RAISE_EXCEPTIONS = DEBUG

#SOCIAL_AUTH_USER_MODEL = 'core.Participant'
#AUTH_USER_MODEL = 'models.User'


# websockets configuration
WEBSOCKET_PORT = 8882;

# celerybeat configuration
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERYBEAT_MAX_LOOP_INTERVAL = 5
CELERYBEAT_LOG_FILE = 'celerybeat.log'
CELERYBEAT_LOG_LEVEL = 'ERROR'

# activation window
ACCOUNT_ACTIVATION_DAYS = 30

DEFAULT_FROM_EMAIL = 'commons@asu.edu'

# use email as username for authentication
AUTHENTICATION_BACKENDS = (
    # 'cas.backends.CASBackend',
    'vcweb.core.backends.ParticipantCASBackend',
    "vcweb.core.backends.EmailAuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
)

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

# css classes for django messages, disabled due to use of bootstrap_messages
# MESSAGE_TAGS = {
#     messages.constants.INFO: 'ui-state-highlight ui-corner-all',
#     messages.constants.WARNING: 'ui-state-error ui-corner-all',
#     messages.constants.ERROR: 'ui-state-error ui-corner-all'
# }

def is_accessible(directory_path):
    return path.isdir(directory_path) and os.access(directory_path, os.W_OK | os.X_OK)

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

# logging configuration
VCWEB_LOG_FILENAME = 'vcweb.log'

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
        'sentry': {
            'level': 'ERROR',
            'formatter': 'verbose',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'vcweb_verbose',
        },
        'vcweb.file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'vcweb_verbose',
            'filename': path.join(LOG_DIRECTORY, VCWEB_LOG_FILENAME),
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
            'handlers': ['vcweb.file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# for django-debug-toolbar
INTERNAL_IPS = ('127.0.0.1', '68.99.87.185',)
# FIXME: hacky, see
# http://stackoverflow.com/questions/8219940/how-do-i-access-imported-local-settings-without-a-circular-import
# for other solutions
has_local_settings = False
try:
    import settings_local
    has_local_settings = True
except ImportError:
    has_local_settings = False


def add_settings_tuples(varname, settings_local):
    settings_local_tuple = getattr(settings_local, varname, None)
    original_settings_tuple = globals()[varname]
    if settings_local_tuple is not None:
    #    print "adding local setting %s to existing %s %s" % (settings_local_tuple, varname, original_settings_tuple)
        globals()[varname] = original_settings_tuple + settings_local_tuple


if has_local_settings:
    try:
        DEBUG = getattr(settings_local, 'DEBUG', DEBUG)
        SENTRY_DSN = getattr(settings_local, 'SENTRY_DSN', None)
        EMAIL_BACKEND = getattr(settings_local, 'EMAIL_BACKEND', EMAIL_BACKEND)
        DATABASES = getattr(settings_local, 'DATABASES', DATABASES)
        SECRET_KEY = getattr(settings_local, 'SECRET_KEY', SECRET_KEY)
        SITE_URL = getattr(settings_local, 'SITE_URL', SITE_URL)
        BITBUCKET_API_USER = getattr(settings_local, 'BITBUCKET_API_USER', BITBUCKET_API_USER)
        BITBUCKET_API_PW = getattr(settings_local, 'BITBUCKET_API_PW', BITBUCKET_API_PW)
        add_settings_tuples('MIDDLEWARE_CLASSES', settings_local)
        add_settings_tuples('INSTALLED_APPS', settings_local)
        add_settings_tuples('ALLOWED_HOSTS', settings_local)
    except Exception as e:
        print "unexpected error while importing local settings: %s" % e
        pass
DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
}

# Required by the System if using CAS
CAS_UNIVERSITY_NAME = "Arizona State University"
CAS_UNIVERSITY_URL = "http://www.asu.edu"
WEB_DIRECTORY_URL = "https://webapp4.asu.edu/directory/ws/search?asuriteId="

# Required settings for CAS Library
CAS_SERVER_URL = "https://weblogin.asu.edu/cas/"
CAS_IGNORE_REFERER = True
# CAS_LOGOUT_COMPLETELY = True
# CAS_PROVIDE_URL_TO_LOGOUT = True
CAS_REDIRECT_URL = "/cas/asu"

CAS_RESPONSE_CALLBACKS = (
    'vcweb.core.views.get_cas_user',
)
CAS_CUSTOM_FORBIDDEN = 'cas_error'
