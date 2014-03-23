from cas.backends import CASBackend
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.core.validators import validate_email
from vcweb import settings
from vcweb.core.models import Participant, Institution
from vcweb.core.views import ASUWebDirectoryProfile, PermissionDenied
import logging

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
                # check for and handle participants logging in with an auth code?
        except User.DoesNotExist:
            logger.warning("no user found with username %s", username)
        except:
            logger.warning("username wasn't a valid email: %s", username)
        return None


class ParticipantCASBackend(CASBackend):
    """
    CAS authentication backend with some user data populated from ASU's Web Directory.

    Primary responsibility is to modify the Django user details and create vcweb Participant if the user was
    created by the CAS (i.e user logging in is a new user)
    1. Get details from the ASU web directory (FIXME: this is brittle and specific to ASU, will need to update if we
        ever roll CAS login out for other institutions)
        a. If the user is an undergrad student then populate the Django user / vcweb Participant with the details
            fetched from the ASU web Directory.
        b. If the user is not an undergrad student then don't create the vcweb participant for that user and
            Redirect such users to error page. Moreover delete the newly created user.
    """

    def authenticate(self, ticket, service):
        """Authenticates CAS ticket and retrieves user data"""
        user = super(ParticipantCASBackend, self).authenticate(ticket, service)

        # If user is not in the system then an user with empty fields will be created by the CAS.
        # Update the user details by fetching the data from the University Web Directory

        if is_new_user(user):
            directory_profile = ASUWebDirectoryProfile(user.username)
            email = directory_profile.email
            logger.debug("%s (%s)", directory_profile, email)

            # Create vcweb Participant only if the user is an undergrad student
            if directory_profile.is_undergraduate:

                user.first_name = directory_profile.first_name
                user.last_name = directory_profile.last_name
                user.email = directory_profile.email
                password = User.objects.make_random_password()
                user.set_password(password)
                institution = Institution.objects.get(name='Arizona State University')
                user.save()
                participant = Participant.objects.create(user=user, major=directory_profile.major,
                        institution=institution, institution_username=user.username)
                logger.debug("CAS backend created participant %s from web directory", participant)
            else:
                logger.debug("XXX: CAS authenticated user %s is not an undergrad student, deleting", user)
                # Delete the user as it has an "unusable" password
                user.delete()
                raise PermissionDenied(
                    "Registration is only available to ASU undergraduates. Please contact us for more information.")
        return user


def is_new_user(user):
    """ returns true iff the user has an empty email, first name, and last name """
    return not user.email and not user.first_name and not user.last_name
