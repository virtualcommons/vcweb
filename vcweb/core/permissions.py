import logging

from rest_framework import permissions

logger = logging.getLogger(__name__)


class CanEditExperiment(permissions.IsAuthenticatedOrReadOnly):

    def has_object_permission(self, request, view, experiment):
        user = request.user
        return (
            user.is_superuser or
            (experiment.published and request.method in permissions.SAFE_METHODS) or
            (user.is_authenticated() and experiment.is_editable_by(user))
        )
