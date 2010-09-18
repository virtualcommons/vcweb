'''

General VCWEB Authentication backend.  There are a few use cases needed:

1. Users can login as Experimenters or Participants.  

code adapted from http://djangosnippets.org/snippets/74/
and http://scottbarnham.com/blog/2008/08/21/extending-the-django-user-model-with-inheritance/

'''


from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import email_re
import logging

logger = logging.getLogger('vcweb.core.auth')

# FIXME: check for and handle Participant experiment auth codes.
class AuthenticationBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            try:
                user = User.objects.get(email=username)
                if user.check_password(password):
                    return user
                # check for and handle participants logging in with an auth?
            except User.DoesNotExist:
                return None
        return None
