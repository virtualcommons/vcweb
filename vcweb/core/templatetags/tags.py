### tags.py
### custom template tags
### active tag taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

from django import template
from django.conf import settings
import os
import re
register = template.Library()

import logging

logger = logging.getLogger(__name__)

@register.simple_tag
def active(request, pattern):
    return 'active' if pattern == request.path else 'inactive'

@register.simple_tag
def active_re(request, pattern):
    return 'active' if re.search(pattern, request.path) else 'inactive'

@register.filter
def mkrange(value):
    return range(value)

@register.filter(name='addcss')
def addcss(field, css):
   return field.as_widget(attrs={"class":css})

@register.simple_tag
def build_id():
    build_id_file_path = os.path.join(settings.SETTINGS_PATH, '../build-id.txt')
    try:
        with open(build_id_file_path, 'r') as f:
            return f.read()
    except:
        logger.error("no build id file found at %s", build_id_file_path)
        return '1'


