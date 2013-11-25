from django.shortcuts import redirect

from django.contrib.auth.decorators import user_passes_test

from dajaxice.core import dajaxice_functions

from vcweb.core.models import is_experimenter, is_participant

import logging
logger = logging.getLogger(__name__)

def dajaxice_register(wrapped_function):
    dajaxice_functions.register(wrapped_function)
    return wrapped_function

def is_anonymous(user):
    return user is None or not user.is_authenticated()

def anonymous_required(view_function=None, redirect_to='core:dashboard'):
    return create_user_decorator(view_function, is_anonymous, redirect_to=redirect_to)
    #return create_decorator(view_function, is_anonymous)

def experimenter_required(view_function=None):
    return create_decorator(view_function, is_experimenter)

def participant_required(view_function=None):
    return create_decorator(view_function, is_participant)

def create_decorator(view_function, is_valid_user):
    actual_decorator = user_passes_test(is_valid_user)
    return actual_decorator if view_function is None else actual_decorator(view_function)

def create_user_decorator(view_function, is_valid_user, redirect_to='core:dashboard'):
    def decorator(fn):
        def _decorated_view(request, *args, **kwargs):
            if is_valid_user(request.user):
                logger.debug('user was valid: %s', request.user)
                return fn(request, *args, **kwargs)
            else:
                logger.debug('user was invalid, redirecting to %s', redirect_to)
                return redirect(redirect_to)
        _decorated_view.__name__ = fn.__name__
        _decorated_view.__dict__ = fn.__dict__
        _decorated_view.__doc__ = fn.__doc__
        return _decorated_view
    return decorator if view_function is None else decorator(view_function)


def concurrency_test(times):
    """
    Add this decorator to small pieces of code that you want to test
    concurrently to make sure they don't raise exceptions when run at the
    same time.  E.g., some Django views that do a SELECT and then a subsequent
    INSERT might fail when the INSERT assumes that the data has not changed
    since the SELECT.
    """
    def test_concurrently_decorator(test_func):
        def wrapper(*args, **kwargs):
            exceptions = []
            import threading
            def call_test_func():
                try:
                    test_func(*args, **kwargs)
                except Exception, e:
                    exceptions.append(e)
                    raise

            threads = []
            for i in range(times):
                threads.append(threading.Thread(target=call_test_func))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if exceptions:
                raise Exception('test_concurrently intercepted %s exceptions: %s' % (len(exceptions), exceptions))
                #logger.debug("I was here!!!")
        return wrapper
    return test_concurrently_decorator