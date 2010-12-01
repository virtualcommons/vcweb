#!/usr/bin/python2.6

import os
import sys

path = '/opt/webapps/virtualcommons/'

if path not in sys.path:
    sys.path.append(path)

os.environ["CELERY_LOADER"] = "django"
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
