#!/usr/bin/env python

from gevent import monkey; monkey.patch_all()
from gevent import WSGIServer

import sys
import os

sys.path.append('..')
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'


