# Django settings for vcweb project.

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Allen Lee', 'allen.lee@asu.edu'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'vcweb'             # Or path to database file if using sqlite3.
DATABASE_USER = 'vcweb'             # Not used with sqlite3.
DATABASE_PASSWORD = 'CUSTOMIZE_ME'         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/'

# django celery integration
# celery rabbitmq/amqp configuration
BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "vcweb"
BROKER_VHOST = "vcweb.vhost"
BROKER_PASSWORD = 'CUSTOMIZE_ME'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'CUSTOMIZE_ME'

SOCKET_IO_HOST = "vcweb.asu.edu"
EMAIL_HOST = "smtp.asu.edu"

