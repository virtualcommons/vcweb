from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
import traceback
import sys
from minidetector import Middleware as minidetector_middleware

import logging

logger = logging.getLogger(__name__)

def detect_mobile(request):
    minidetector_middleware.process_request(request)
    return request

class ExceptionHandlingMiddleware(object):
    def process_exception(self, request, exception):
        logger.error(traceback.format_exception(*sys.exc_info()))
        if type(exception) == PermissionDenied:
            if request.user.is_authenticated():
                messages.warning(request, exception)
                return redirect('core:dashboard')
        return None
