from django.shortcuts import redirect

from vcweb.core.models import is_experimenter, is_participant

import logging
logger = logging.getLogger(__name__)

def is_anonymous(user):
    return user is None or not user.is_authenticated()

def anonymous_required(view_function=None, redirect_to='core:dashboard'):
    #    return create_user_decorator(view_function, lambda user: user is none or not user.is_authenticated(), redirect_to=redirect_to)
    return create_user_decorator(view_function, is_anonymous, redirect_to=redirect_to)

def experimenter_required(view_function=None, redirect_to='core:dashboard'):
    return create_user_decorator(view_function, is_experimenter, redirect_to=redirect_to)

def participant_required(view_function=None, redirect_to='core:dashboard'):
    return create_user_decorator(view_function, is_participant, redirect_to=redirect_to)


def create_user_decorator(view_function, is_valid_user, redirect_to=None):
    def decorator(fn):
        def _decorated_view(request, *args, **kwargs):
            if is_valid_user(request.user):
                logger.debug('user was valid: %s' % request.user)
                return fn(request, *args, **kwargs)
            else:
                logger.debug('user was invalid, redirecting to %s' % redirect_to)
                return redirect(redirect_to)
        ''' alias the decorator name, dict, and doc strings (is this necessary?) '''
        _decorated_view.__name__ = fn.__name__
        _decorated_view.__dict__ = fn.__dict__
        _decorated_view.__doc__ = fn.__doc__
        return _decorated_view
    return decorator if view_function is None else decorator(view_function)
'''
         def _view(request, *args, **kwargs):
-            if request.user is not None and request.user.is_authenticated():
                 return HttpResponseRedirect(redirect_to)
-            else:
-                return view_function(request, *args, **kwargs)
-        _view.__name__ = view_function.__name__
-        _view.__dict__ = view_function.__dict__
-        _view.__doc__ = view_function.__doc__
-        return _view
'''
