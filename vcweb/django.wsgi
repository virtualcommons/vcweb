#!/usr/bin/python2.6

import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
