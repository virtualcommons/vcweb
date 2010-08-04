'''

General VCWEB Authentication backend.  There are a few use cases needed:

1. Users can login as Experimenters or Participants.  

code adapted from http://djangosnippets.org/snippets/74/
and http://scottbarnham.com/blog/2008/08/21/extending-the-django-user-model-with-inheritance/

'''


from django.contrib.auth.backends import ModelBackend

from django.core.validators import email_re
from vcweb.core.models import *



logger = logging.getLogger('vcweb.core.auth')

def is_experimenter(user):
    try:
        return user.experimenter
    except Experimenter.DoesNotExist:
        return None

def is_participant(user):
    try:
        return user.participant
    except Participant.DoesNotExist:
        return None

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

