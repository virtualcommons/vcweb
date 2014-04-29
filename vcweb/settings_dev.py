# Local Development Django settings for vcweb
DEBUG = True
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
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'vcweb',
            'USER': 'vcweb',
            'PASSWORD': 'CUSTOMIZE_ME',
            }
        }
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
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

# need to override this appropriately for foursquare geolocation queries
FOURSQUARE_CONSUMER_KEY      = ''
FOURSQUARE_CONSUMER_SECRET   = ''

# override these appropriately for fb connect
FACEBOOK_APP_ID              = ''
FACEBOOK_API_SECRET          = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'CUSTOMIZE_ME'

# use debug_toolbar and sslserver in dev mode
INSTALLED_APPS = ('debug_toolbar','sslserver',)
MIDDLEWARE_CLASSES = (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
        )


