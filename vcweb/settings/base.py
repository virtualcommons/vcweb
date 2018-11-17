"""
For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

from enum import Enum
import configparser
import logging
import os


class Environment(Enum):
    PRODUCTION = 1
    STAGING = 2
    DEVELOPMENT = 3

    @property
    def is_production(self):
        return self.value == 1

    @property
    def is_staging(self):
        return self.value == 2

    @property
    def is_development(self):
        return self.value == 3


# valid values: 'DEVELOPMENT', 'STAGING', 'PRODUCTION'
ENVIRONMENT = Environment.DEVELOPMENT

# see https://github.com/kraiz/django-crontab
CRONJOBS = [
    ('0 0 * * *', 'vcweb.cron.system_daily_tick'),
    ('0 0 * * 0', 'vcweb.cron.system_weekly_tick'),
    ('0 0 1 * *', 'vcweb.cron.system_monthly_tick'),
]

DEBUG = True

USE_TZ = False

SITE_URL = 'http://localhost:8000'
SITE_ID = 1

# set BASE_DIR one level up since we're in a settings directory.
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# base directory is one level above the project directory
BASE_DIR = os.path.dirname(PROJECT_DIR)

# GITHUB
GITHUB_URL = "https://api.github.com"
GITHUB_ACCESS_TOKEN = "ADD YOUR ACCESS TOKEN TO LOCAL SETTINGS FILE"
GITHUB_REPO = "vcweb"
GITHUB_REPO_OWNER = "virtualcommons"
GITHUB_ISSUE_LABELS = ["bug"]

SUBJECT_POOL_WAITLIST_SIZE = 10

DEMO_EXPERIMENTER_EMAIL = 'vcweb@mailinator.com'
DEFAULT_EMAIL = DEFAULT_FROM_EMAIL = 'vcweb@asu.edu'
EMAIL_HOST = 'smtp.asu.edu'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
ALLOWED_HOSTS = ('.asu.edu', 'localhost',)
ADMINS = (
    ('Allen Lee', 'allen.lee@asu.edu'),
)
MANAGERS = ADMINS

DATA_DIR = 'data'

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

# configure secrets / config.ini
config = configparser.ConfigParser()

config.read('/secrets/config.ini')

# default from email for various automated emails sent by Django
DEFAULT_FROM_EMAIL = config.get('email', 'DEFAULT_FROM_EMAIL', fallback='commons@asu.edu')
# email address used for errors emails sent to ADMINS and MANAGERS
SERVER_EMAIL = config.get('email', 'SERVER_EMAIL', fallback='commons@asu.edu')
# recaptcha config
RECAPTCHA_PUBLIC_KEY = config.get('captcha', 'RECAPTCHA_PUBLIC_KEY', fallback='')
RECAPTCHA_PRIVATE_KEY = config.get('captcha', 'RECAPTCHA_PRIVATE_KEY', fallback='')

RAVEN_CONFIG = {
    'dsn': config.get('logging', 'SENTRY_DSN', fallback=''),
    'public_dsn': config.get('logging', 'SENTRY_PUBLIC_DSN', fallback=''),
    # If you are using git, you can also automatically configure the
    # release based on the git info.
    # 'release': raven.fetch_git_sha(BASE_DIR),
}

# Make this unique, and don't share it with anybody.
SECRET_KEY = config.get('django', 'SECRET_KEY')

# Database configuration
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config.get('database', 'DB_NAME'),
        'USER': config.get('database', 'DB_USER'),
        'PASSWORD': config.get('database', 'DB_PASSWORD'),
        'HOST': config.get('database', 'DB_HOST'),
        'PORT': config.get('database', 'DB_PORT'),
    }
}

CSRF_FAILURE_VIEW = 'vcweb.core.views.csrf_failure'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.tz',
                'dealer.contrib.django.context_processor',
                'vcweb.core.context_processors.common',
            ],
        },
    },
]

MIDDLEWARE = [
    'raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',
    'raven.contrib.django.raven_compat.middleware.SentryResponseErrorIdMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cas.middleware.CASMiddleware',
]


ROOT_URLCONF = 'vcweb.urls'

# cookie storage vs session storage of django messages
# MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
REDIS_HOST = "redis"
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # FIXME: switch to TCP in prod
        'LOCATION': 'redis://{}:6379/1'.format(REDIS_HOST),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

DJANGO_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
)

THIRD_PARTY_APPS = (
    'raven.contrib.django.raven_compat',
    'contact_form',
    'django_extensions',
    'mptt',
    'bootstrap3',
    'cas',
    'django_redis',
    'django_crontab',
)


VCWEB_EXPERIMENTS = (
    'vcweb.experiment.forestry',
    'vcweb.experiment.lighterprints',
    'vcweb.experiment.bound',
    'vcweb.experiment.irrigation',
)

VCWEB_APPS = ('vcweb.core', 'vcweb.core.subjectpool',) + VCWEB_EXPERIMENTS

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + VCWEB_APPS

LOGIN_REDIRECT_URL = '/dashboard'

# websockets configuration
WEBSOCKET_SSL = False
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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_DIRS = [
    os.path.join(PROJECT_DIR, "static"),
]

STATIC_ROOT = '/shared/static'
STATIC_URL = '/static/'

# Absolute path to the directory that holds media (user uploads).
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/shared/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'


def is_accessible(directory_path):
    return os.path.isdir(directory_path) and os.access(directory_path, os.W_OK | os.X_OK)


LOG_DIRECTORY = config.get('logging', 'LOG_DIRECTORY', fallback=os.path.join(BASE_DIR, 'logs'))

if not is_accessible(LOG_DIRECTORY):
    try:
        os.makedirs(LOG_DIRECTORY)
    except OSError:
        print(("Unable to create absolute log directory at {}, setting to relative path logs instead".format(LOG_DIRECTORY)))
        LOG_DIRECTORY = 'logs'
        if not is_accessible(LOG_DIRECTORY):
            try:
                os.makedirs(LOG_DIRECTORY)
            except OSError:
                print("Couldn't create any log directory, startup will fail")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'DEBUG',
        'handlers': ['vcweb.file', 'console'],
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
        'raven': {
            'level': 'DEBUG',
            'handlers': ['vcweb.file', 'console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['vcweb.file', 'console'],
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'vcweb': {
            'handlers': ['vcweb.file', 'console', 'sentry'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

# Required if using CAS
CAS_UNIVERSITY_NAME = "Arizona State University"
CAS_UNIVERSITY_URL = "http://www.asu.edu"

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

# override in local.py to enable more verbose logging e.g.,
# DISABLED_TEST_LOGLEVEL = logging.NOTSET
DISABLED_TEST_LOGLEVEL = logging.DEBUG

# revision reporting support using dealer
DEALER_TYPE = 'git'
DEALER_SILENT = True
DEALER_BACKENDS = ('git',)
DEALER_PATH = BASE_DIR
