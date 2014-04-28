from functools import wraps
from django.shortcuts import redirect

from django.contrib.auth.decorators import user_passes_test


import time
import logging

logger = logging.getLogger(__name__)


def log_signal_errors(signal_sender):
    @wraps(signal_sender)
    def error_checker(*args, **kwargs):
        results = signal_sender(*args, **kwargs)
        for receiver, response in results:
            if response is not None:
                logger.error("errors while dispatching to %s: %s", receiver, response)
    return error_checker

def is_anonymous(user):
    return user is None or not user.is_authenticated()


def anonymous_required(view_function=None, redirect_to='core:dashboard'):
    return create_user_decorator(view_function, is_anonymous, redirect_to=redirect_to)
    #return create_decorator(view_function, is_anonymous)


def experimenter_required(view_function=None):
    from vcweb.core.models import is_experimenter
    return create_decorator(view_function, is_experimenter)


def participant_required(view_function=None):
    from vcweb.core.models import is_participant
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


def retry(exceptiontocheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param exceptiontocheck: the exception to check. may be a tuple of
        exceptions to check
    :type exceptiontocheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptiontocheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.debug(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry
