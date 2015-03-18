# tags.py
# custom template tags
# active tag taken from
# http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

import os
import re

from django import template
from django.conf import settings
from django.contrib.auth.models import Group

register = template.Library()

import logging

logger = logging.getLogger(__name__)


@register.simple_tag
def active(request, pattern):
    if request:
        return 'active' if pattern == request.path else 'inactive'
    else:
        return 'inactive'


@register.simple_tag
def active_re(request, pattern):
    if request:
        return 'active' if re.search(pattern, request.path) else 'inactive'
    return 'inactive'


@register.filter(name='has_group')
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False
