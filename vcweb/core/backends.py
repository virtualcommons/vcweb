import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.validators import validate_email
from django.db.models import Q

logger = logging.getLogger(__name__)


class EmailAuthenticationBackend(ModelBackend):

    """
    allow users to login with their email as their username,

    FIXME: check for and handle Participant experiment auth codes separately from actual login
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        lowercase_username = username.lower()
        try:
            if '@' in lowercase_username:
                validate_email(lowercase_username)
            user = UserModel.objects.get(Q(email=lowercase_username) | Q(username=lowercase_username))
            if user.check_password(password):
                return user
            # TODO: at some point should check for participants logging in with an auth code
        except UserModel.DoesNotExist:
            logger.warning("no user found with username %s", username)
        return None
