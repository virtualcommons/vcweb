import logging

from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect


class ExceptionHandlingMiddleware(object):
    def process_exception(self, request, exception):
        logging.exception('unhandled exception while processing request %s', request)
        if type(exception) == PermissionDenied and request.user.is_authenticated():
            messages.warning(request, exception)
            return redirect('core:dashboard')
        return None
