import logging
import time
from functools import wraps

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def log_signal_errors(signal_sender):
    @wraps(signal_sender)
    def error_checker(*args, **kwargs):
        results = signal_sender(*args, **kwargs)
        if results:
            for receiver, response in results:
                if isinstance(response, Exception):
                    logger.error("errors while dispatching to %s", receiver)
                    logger.exception(response)
    return error_checker


def is_anonymous(user):
    return user is None or not user.is_authenticated()


def anonymous_required(view_function=None, redirect_to='home'):
    return create_user_decorator(view_function, is_anonymous, redirect_to=redirect_to)


def is_experimenter(user, experimenter=None):
    """
    returns true if user.experimenter exists and is an Experimenter instance.  If an experimenter is passed in as a
    keyword argument, adds the additional constraint that user.experimenter == experimenter
    """
    return hasattr(user, 'experimenter') and user.experimenter.is_valid(experimenter)


def is_participant(user):
    """
    returns true iff user.participant exists, is active
    """
    return hasattr(user, 'participant') and user.is_active


def group_required(*permission_groups, **kwargs):
    """Requires user membership in at least one of the groups passed in."""
    def in_groups(u):
        if u.is_authenticated() and u.is_active:
            group_names = [pg.value for pg in permission_groups]
            return u.groups.filter(name__in=group_names).exists()
    return user_passes_test(in_groups)


def create_user_decorator(view_function, is_valid_user, redirect_to='core:login'):
    def _decorator(fn):
        @wraps(fn)
        def _decorated_view(request, *args, **kwargs):
            user = request.user
            if is_valid_user(user):
                logger.debug('user %s was valid via test %s', user, is_valid_user)
                return fn(request, *args, **kwargs)
            else:
                logger.debug('user %s was deemed invalid with %s, redirecting to %s', user, is_valid_user, redirect_to)
                return redirect(redirect_to)
        return _decorated_view

    return _decorator if view_function is None else _decorator(view_function)


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
                except exceptiontocheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.debug(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)
        return f_retry  # true decorator
    return deco_retry


def ownership_required(model_class, attr_name='pk'):
    """ Decorator to verify the ownership permission on the Object of provided model_class and pk

    :param model_class: Model class whose instance with pk we want to check object ownership permissions
    :param attr_name: The name of the pk attribute bound incoming from a url pattern match
    """
    def decorator(view_function):
        def wrap(request, *args, **kwargs):
            pk = kwargs.get(attr_name, None)

            if pk is None:
                raise RuntimeError('No pk argument was found in {}'.format(kwargs))
            is_owner_func = getattr(model_class, 'is_owner', None)  # should return an unbound function

            if is_owner_func is None:
                raise RuntimeError('model class {} must define an is_owner instance method)'.format(model_class))

            try:
                obj = model_class.objects.get(pk=pk)  # raises ObjectDoesNotExist
                if obj.is_owner(request.user):
                    return view_function(request, *args, **kwargs)
            except model_class.DoesNotExist:
                logger.error("No instance of %s found with pk %s", model_class, pk)

            logger.warning("unauthorized access to %s Model by user %s", model_class, request.user)
            raise PermissionDenied
        return wraps(view_function)(wrap)
    return decorator
