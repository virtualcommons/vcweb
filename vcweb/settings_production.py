# Django settings for vcweb project.
import sys

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Allen Lee', 'allen.lee@asu.edu'),
)
MANAGERS = ADMINS

CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
            }
        }

DATABASES = {
        'default': {
            'ENGINE': 'sqlite3' if 'test' in sys.argv else 'django.db.backends.postgresql_psycopg2',
            'NAME': 'vcweb',
            'USER': 'vcweb',
            'PASSWORD': 'CUSTOMIZE_ME',
            }
        }
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
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
# XXX: no i18n for the time being
USE_I18N = False

# django celery integration
# celery rabbitmq/amqp configuration
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "vcweb"
BROKER_VHOST = "vcweb.vhost"
BROKER_PASSWORD = 'CUSTOMIZE_ME'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'CUSTOMIZE_ME'
