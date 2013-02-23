from django.contrib import messages
from os import path, makedirs

DEBUG = True
TEMPLATE_DEBUG = DEBUG

USE_TZ = False

SERVER_EMAIL='vcweb@asu.edu'
SERVER_NAME='vcweb.asu.edu'
EMAIL_HOST='smtp.asu.edu'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ALLOWED_HOSTS = ('.asu.edu', 'localhost',)
ADMINS = (
        ('Allen Lee', 'allen.lee@asu.edu')
        )

MANAGERS = ADMINS

DATA_DIR = 'data'

GRAPH_DATABASE_PATH=path.join(DATA_DIR, 'neo4j-store')

DATABASES = {
        'sqlite': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': path.join(DATA_DIR, 'vcweb.db'),
            },
        'default': {
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
        'vcweb.lighterprints',
        'vcweb.boundaries',
        'vcweb.broker',
#        'vcweb.sanitation',
        'dajaxice',
        'raven.contrib.django',
        'kronos',
        'south',
        'social_auth',
        'django_extensions',
        'mptt',
        'bootstrap',
        )

SOUTH_TESTS_MIGRATE = False

DAJAXICE_MEDIA_PREFIX = "dajaxice"

STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        'dajaxice.finders.DajaxiceFinder',
        )

# django social auth keys
TWITTER_CONSUMER_KEY         = ''
TWITTER_CONSUMER_SECRET      = ''
FACEBOOK_APP_ID              = ''
FACEBOOK_API_SECRET          = ''
FACEBOOK_EXTENDED_PERMISSIONS = ['email']
LINKEDIN_CONSUMER_KEY        = ''
LINKEDIN_CONSUMER_SECRET     = ''
GOOGLE_CONSUMER_KEY          = ''
GOOGLE_CONSUMER_SECRET       = ''
GOOGLE_OAUTH2_CLIENT_ID      = ''
GOOGLE_OAUTH2_CLIENT_SECRET  = ''
FOURSQUARE_CONSUMER_KEY      = ''
FOURSQUARE_CONSUMER_SECRET   = ''
FOURSQUARE_OAUTH_ENDPOINT = 'https://foursquare.com/oauth2/authenticate'
FOURSQUARE_OAUTH_ACCESS_TOKEN_ENDPOINT = 'https://foursquare.com/oauth2/access_token'
FOURSQUARE_VENUE_SEARCH_ENDPOINT = 'https://api.foursquare.com/v2/venues/search'
FOURSQUARE_CATEGORIES_ENDPOINT = 'https://api.foursquare.com/v2/venues/categories'
FOURSQUARE_CONSUMER_DATE_VERIFIED = '20120417'
GITHUB_APP_ID                = ''
GITHUB_API_SECRET            = ''
DROPBOX_APP_ID               = ''
DROPBOX_API_SECRET           = ''
FLICKR_APP_ID                = ''
FLICKR_API_SECRET            = ''
INSTAGRAM_CLIENT_ID          = ''
INSTAGRAM_CLIENT_SECRET      = ''

LOGIN_REDIRECT_URL = '/dashboard'
LOGIN_ERROR_URL    = '/login-error/'
#LOGIN_REDIRECT_URL='/dashboard'
#LOGIN_ERROR_URL='/accounts/login/error'
SOCIAL_AUTH_COMPLETE_URL_NAME  = 'socialauth_complete'
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
        'social_auth.backends.twitter.TwitterBackend',
        'social_auth.backends.facebook.FacebookBackend',
#        'social_auth.backends.google.GoogleOAuthBackend',
        'social_auth.backends.google.GoogleOAuth2Backend',
        'social_auth.backends.google.GoogleBackend',
        'social_auth.backends.yahoo.YahooBackend',
#        'social_auth.backends.browserid.BrowserIDBackend',
        'social_auth.backends.contrib.linkedin.LinkedinBackend',
#        'social_auth.backends.contrib.livejournal.LiveJournalBackend',
#        'social_auth.backends.contrib.orkut.OrkutBackend',
        'social_auth.backends.contrib.foursquare.FoursquareBackend',
        'social_auth.backends.contrib.github.GithubBackend',
#        'social_auth.backends.contrib.dropbox.DropboxBackend',
        'social_auth.backends.contrib.flickr.FlickrBackend',
#        'social_auth.backends.contrib.instagram.InstagramBackend',
        'social_auth.backends.OpenIDBackend',
        "vcweb.core.auth.AuthenticationBackend",
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

# set up jquery-ui css classes for django messages
MESSAGE_TAGS = {
        messages.constants.INFO : 'ui-state-highlight ui-corner-all',
        messages.constants.WARNING: 'ui-state-error ui-corner-all',
        messages.constants.ERROR: 'ui-state-error ui-corner-all'
        }


LOG_DIRECTORY = '/opt/vcweb/logs'
try:
    makedirs(LOG_DIRECTORY)
except OSError:
    print "Unable to create log directory at %s" % LOG_DIRECTORY
    pass

# logging configuration
VCWEB_LOG_FILENAME = 'vcweb.log'
TORNADO_LOG_FILENAME = 'tornadio.log'
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
             # according to http://raven.readthedocs.org/en/latest/config/django.html should be
             # 'class': 'raven.contrib.django.handlers.SentryHandler',
             'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',

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
        'tornado.file': {
            'level': 'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'vcweb_verbose',
            'filename': path.join(LOG_DIRECTORY, TORNADO_LOG_FILENAME),
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
        'sockjs.vcweb': {
            'handlers': ['tornado.file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

# for django-debug-toolbar
INTERNAL_IPS = ('127.0.0.1','68.99.87.185',)
# FIXME: hacky, see
# http://stackoverflow.com/questions/8219940/how-do-i-access-imported-local-settings-without-a-circular-import
# for other solutions
try:
    import settings_local as local
    has_local_settings = True
except ImportError:
    print "no local settings found.  create settings_local.py to override settings in a hg-ignored file"
    has_local_settings = False

if has_local_settings:
    try:
        DEBUG = local.DEBUG
        SENTRY_DSN = local.SENTRY_DSN
        for l in local.MIDDLEWARE_CLASSES:
            if l not in MIDDLEWARE_CLASSES:
                MIDDLEWARE_CLASSES += (l,)
        for l in local.INSTALLED_APPS:
            if l not in INSTALLED_APPS:
                INSTALLED_APPS += (l,)
    except:
        pass
# for django-debug-toolbar
INTERNAL_IPS = ('127.0.0.1','68.99.87.185',)
DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        }
