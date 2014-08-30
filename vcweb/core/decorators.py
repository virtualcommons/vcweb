from functools import wraps
import time
import logging

from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

logger = logging.getLogger(__name__)


def log_signal_errors(signal_sender):
    @wraps(signal_sender)
    def error_checker(*args, **kwargs):
        results = signal_sender(*args, **kwargs)
        if results:
            for receiver, response in results:
                if response is not None:
                    logger.error(
                        "errors while dispatching to %s: %s", receiver, response)
    return error_checker


def is_anonymous(user):
    return user is None or not user.is_authenticated()


def anonymous_required(view_function=None, redirect_to='core:dashboard'):
    return create_user_decorator(view_function, is_anonymous, redirect_to=redirect_to)


def is_experimenter(user, experimenter=None):
    """
    returns true if user.experimenter exists and is an Experimenter instance.  If an experimenter is passed in as a
    keyword argument, adds the additional constraint that user.experimenter == experimenter
    """
    return hasattr(user, 'experimenter') and user.experimenter.approved and (experimenter is None
                                                                             or user.experimenter == experimenter)


def is_participant(user):
    """
    returns true if user.participant exists and is a Participant instance.
    """
    return hasattr(user, 'participant') and user.is_active


def group_required(*permissions):
    """Requires user membership in at least one of the groups passed in."""
    def in_groups(u):
        if u.is_authenticated() and ((hasattr(u, 'experimenter') and u.experimenter.approved) or (hasattr(u, 'participant') and u.is_active)):
            group_names = [permission.value for permission in permissions]
            logger.debug(group_names)
            return u.is_superuser or bool(u.groups.filter(name__in=group_names))
    return user_passes_test(in_groups)


def create_user_decorator(view_function, is_valid_user, redirect_to='core:dashboard'):
    def decorator(fn):
        def _decorated_view(request, *args, **kwargs):
            if is_valid_user(request.user):
                logger.debug('user was valid: %s', request.user)
                return fn(request, *args, **kwargs)
            else:
                logger.debug(
                    'user was invalid, redirecting to %s', redirect_to)
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


def ownership_required(model, attr_name='pk'):
    """ Decorator to verify the ownership permission on the Object of provided Model and pk

    :param model: The name of a Model of which the object ownership permission needs to be checked
    :param attr_name: The name by which pk attribute is binded in the url

    """
    def decorator(view_function):
        def wrap(request, *args, **kwargs):
            pk = kwargs.get(attr_name, None)

            if pk is None:
                raise RuntimeError('The decorator requires pk argument to be set (got {} instead)'.format(kwargs))
            is_owner_func = getattr(model, 'is_owner', None)

            if is_owner_func is None:
                raise RuntimeError('The decorator requires model class {} to provide is_owner function)'.format(model))

            try:
                obj = model.objects.get(pk=pk) #raises ObjectDoesNotExist
                if obj.is_owner(request.user):
                    return view_function(request, *args, **kwargs)
            except ObjectDoesNotExist:
                pass

            logger.warning("unauthorized access to %s Model by user %s", model, request.user)
            raise PermissionDenied
        return wraps(view_function)(wrap)
    return decorator
