# tags.py
# custom template tags
# active tag taken from
# http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

import os
import re

from django import template
from django.conf import settings

register = template.Library()

import logging

logger = logging.getLogger(__name__)


@register.simple_tag
def active(request, pattern):
    logger.debug("request: %s, pattern: %s", request, pattern)
    if request:
        return 'active' if pattern == request.path else 'inactive'
    else:
        return 'inactive'


@register.simple_tag
def active_re(request, pattern):
    if request:
        return 'active' if re.search(pattern, request.path) else 'inactive'
    return 'inactive'


@register.filter
def mkrange(value):
    return range(value)


@register.filter(name='addcss')
def addcss(field, css):
    return field.as_widget(attrs={"class": css})


@register.simple_tag
def build_id():
    build_id_file_path = os.path.join(settings.BASE_DIR, os.pardir, 'build-id.txt')
    try:
        with open(build_id_file_path, 'r') as f:
            return f.read()
    except:
        logger.warning("no build id file found at %s", build_id_file_path)
        return '1'
