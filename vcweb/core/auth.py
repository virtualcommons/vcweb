'''

General VCWEB authentication backend to allow users to login with their email
as their username.

code adapted from http://djangosnippets.org/snippets/74/
and http://scottbarnham.com/blog/2008/08/21/extending-the-django-user-model-with-inheritance/

'''


from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import email_re
import logging

logger = logging.getLogger(__name__)

# FIXME: check for and handle Participant experiment auth codes.
class AuthenticationBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            try:
                user = User.objects.get(email=username.lower())
                if user.check_password(password):
                    return user
                # check for and handle participants logging in with an auth code?
            except User.DoesNotExist:
                return None
        return None
