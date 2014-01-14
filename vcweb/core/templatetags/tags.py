### tags.py
### custom template tags
### active tag taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

from django import template
import re
register = template.Library()

import logging

logger = logging.getLogger(__name__)

@register.simple_tag
def active(request, pattern):
    return 'active' if pattern == request.path else 'inactive'

@register.simple_tag
def active_re(request, pattern):
    logger.debug("looking for pattern %s", pattern)
    return 'active' if re.search(pattern, request.path) else 'inactive'

@register.filter
def mkrange(value):
    return range(value)

@register.filter(name='addcss')
def addcss(field, css):
   return field.as_widget(attrs={"class":css})