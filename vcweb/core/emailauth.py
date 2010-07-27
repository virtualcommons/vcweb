'''
code adapted from http://djangosnippets.org/snippets/74/
'''

from django.contrib.auth.backends import ModelBackend
from django.core.validators import email_re
from vcweb.core.models import Experimenter, Participant

class EmailBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        if email_re.search(username):
            person = self.get_user(user_id=username)
            # FIXME: check for Participant game codes.
            if person is not None and person.user.check_password(password):
                return person
        return None
    
    def get_user(self, user_id=None):
        if email_re.search(user_id):
            try:
                return Experimenter.objects.get(user__email=user_id)
            except Experimenter.DoesNotExist:
                try:
                    return Participant.objects.get(user__email=user_id)
                except Participant.DoesNotExist:
                    return None
                
        
    
    