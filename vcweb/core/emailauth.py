'''
code adapted from http://djangosnippets.org/snippets/74/


'''

from django.contrib.auth.backends import ModelBackend
# 1.2 syntax, see http://skyl.org/log/post/skyl/2010/01/email-auth-in-django-email_re-moved-again/
#from django.core.validators import email_re
from django.forms.fields import email_re
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            try:
                user = User.objects.get(email=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                return None
        return None
    
    