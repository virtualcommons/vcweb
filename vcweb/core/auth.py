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



class AuthenticationBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            try:
                user = User.objects.get(email=username)
                # FIXME: check for Participant game codes.
                if user.check_password(password):
                    return user
                # password may be game code.  check it against participant's game game codes.
            except User.DoesNotExist:
                return None
        return None

