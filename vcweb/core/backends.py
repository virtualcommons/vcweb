import logging

from cas.backends import CASBackend
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import validate_email

from .views import PermissionDenied


logger = logging.getLogger(__name__)


class EmailAuthenticationBackend(ModelBackend):

    """
    allow users to login with their email as their username,
    adapted from http://djangosnippets.org/snippets/74/ and
    http://scottbarnham.com/blog/2008/08/21/extending-the-django-user-model-with-inheritance/

    FIXME: should we check for and handle Participant experiment auth codes separately from actual login?
    """

    def authenticate(self, username=None, password=None, **kwargs):
        lowercase_username = username.lower()
        try:
            validate_email(lowercase_username)
            user = User.objects.get(email=lowercase_username)
            if user.check_password(password):
                return user
                # check for and handle participants logging in with an auth
                # code?
        except User.DoesNotExist:
            logger.warning("no user found with username %s", username)
        except:
            logger.warning("username wasn't a valid email: %s", username)
        return None


class ParticipantCASBackend(CASBackend):

    """
    CAS authentication backend with some user data populated from ASU's Web Directory.

    Primary responsibility is to check whether the user was created by the callback or CAS
    1. If the User was created by the cas.
        b. It means the user is not an undergrad student or ASU Web directory was down So Redirect such users to error
        page. Moreover delete the newly created user.
    """

    def authenticate(self, ticket, service):
        """Authenticates CAS ticket and retrieves user data"""
        user = super(ParticipantCASBackend, self).authenticate(ticket, service)

        # If user is not in the system then an user with empty fields will be created by the CAS. So delete that user
        # FIXME: Permission denied error is thrown if the ASU Web Directory is
        # down
        if is_new_user(user):
            logger.error(
                "XXX: CAS authenticated user %s is not an undergrad student, deleting", user)
            # Delete the user as it has an "unusable" password
            user.delete()
            raise PermissionDenied(
                "Registration is only available to ASU undergraduates. Please contact us for more information.")
        return user


def is_new_user(user):
    """ returns true iff the user has an empty email, first name, and last name """
    return not user.email and not user.first_name and not user.last_name
