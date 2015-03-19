from django import template
import logging
import re

logger = logging.getLogger(__name__)
register = template.Library()


@register.simple_tag
def active(request, pattern):
    return 'active' if pattern == request.path else ''


@register.simple_tag
def active_re(request, pattern):
    return 'active' if re.search(pattern, request.path) else ''


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()
