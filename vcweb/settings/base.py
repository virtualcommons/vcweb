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
import pathlib
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


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
# how long to wait (in days) before allowing a potential participant to receive an invitation email for an experiment
# for which they have already been invited
SUBJECT_POOL_INVITATION_DELAY = 5

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
RECAPTCHA_PUBLIC_KEY = config.get('captcha', 'RECAPTCHA_PUBLIC_KEY',
                                  fallback='6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI')
RECAPTCHA_PRIVATE_KEY = config.get('captcha', 'RECAPTCHA_PRIVATE_KEY',
                                   fallback='6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe')

NOCAPTCHA = True

RECAPTCHA_USE_SSL = False

# read in version
RELEASE_VERSION_FILE = "release-version.txt"
release_version_file = pathlib.Path(BASE_DIR, RELEASE_VERSION_FILE)
RELEASE_VERSION = "v2018.11"
if release_version_file.is_file():
    with release_version_file.open('r') as infile:
        RELEASE_VERSION = infile.read().strip()


sentry_sdk.init(
    dsn=config.get('logging', 'SENTRY_DSN', fallback=''),
    integrations=[DjangoIntegration()],
    send_default_pii=True
)

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
        'DIRS': [os.path.dirname(__file__)],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.static',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.tz',
                'vcweb.core.context_processors.common',
            ],
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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
    'captcha',
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

LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# websockets configuration
WEBSOCKET_SSL = False
WEBSOCKET_PORT = 8882
WEBSOCKET_URI = '/websocket'

# activation window
ACCOUNT_ACTIVATION_DAYS = 30


# use email as username for authentication
AUTHENTICATION_BACKENDS = (
    'cas.backends.CASBackend',
    'vcweb.core.backends.EmailAuthenticationBackend',
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

STATIC_ROOT = '/shared/srv/static'
STATIC_URL = '/static/'

# Absolute path to the directory that holds media (user uploads).
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/shared/srv/media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'


def is_accessible(directory_path):
    return os.path.isdir(directory_path) and os.access(directory_path, os.W_OK | os.X_OK)


LOG_DIRECTORY = config.get('logging', 'LOG_DIRECTORY', fallback=os.path.join(BASE_DIR, 'logs'))

for directory in (STATIC_ROOT, MEDIA_ROOT, LOG_DIRECTORY):
    if not is_accessible(directory):
        try:
            os.makedirs(directory)
        except OSError:
            print("Unable to create directory at {}, startup will fail".format(directory))

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
        'vcweb': {
            'handlers': ['vcweb.file', 'console'],
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
