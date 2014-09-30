import logging

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import validate_email


logger = logging.getLogger(__name__)


class EmailAuthenticationBackend(ModelBackend):

    """
    allow users to login with their email as their username,
    adapted from http://djangosnippets.org/snippets/74/ and
    http://scottbarnham.com/blog/2008/08/21/extending-the-django-user-model-with-inheritance/

    FIXME: should we check for and handle Participant experiment auth codes separately from actual login?
    """

    def authenticate(self, username=None, password=None, **kwargs):
        try:
            lowercase_username = username.lower()
            validate_email(lowercase_username)
            user = User.objects.get(email=lowercase_username)
            if user.check_password(password):
                return user
                # check for and handle participants logging in with an auth
                # code?
        except User.DoesNotExist:
            logger.warning("no user found with username %s", username)
        except:
            logger.exception("unhandled exception with username %s", username, exc_info=True)
        return None
