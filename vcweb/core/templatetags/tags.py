### tags.py
### custom template tags
### active tag taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

from django import template
register = template.Library()
import logging
logger = logging.getLogger(__name__)

@register.simple_tag
def active(request, pattern):
    logger.debug("request: %s", request)
    return 'active' if pattern == request.path else 'inactive'

@register.simple_tag
def active_re(request, pattern):
    import re
    return 'active' if re.search(pattern, request.path) else 'inactive'

