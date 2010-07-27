### tags.py
### custom template tags
### active tag taken from http://gnuvince.wordpress.com/2007/09/14/a-django-template-tag-for-the-current-active-page/

from django import template
register = template.Library()

@register.simple_tag
def active(request, pattern):
    import re
    if re.search(pattern, request.path):
        return 'active'
    return ''
