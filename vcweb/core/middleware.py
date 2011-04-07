from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

class ExceptionHandlingMiddleware(object):
    def process_exception(self, request, exception):
        if type(exception) == PermissionDenied:
            if request.user.is_authenticated():
                messages.warning(request, exception)
                return redirect('core:dashboard')
        return None
