from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.functional import curry
import json
import logging

logger = logging.getLogger(__name__)

class VcwebJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, QuerySet):
            return json.loads(serialize('json', obj))
        elif isinstance(obj, Model):
            return json.loads(serialize('json', [obj]))[0]
        else:
            return DjangoJSONEncoder.default(self, obj)

dumps = curry(json.dumps, cls=VcwebJSONEncoder)


# FIXME: deprecate this in favor of django.cache memcached caching?
class simplecache(object):
    """
    only works on no-arg functions that return instances of models that will never change (data parameters,
    experiment metadata, etc.)
    """
    def __init__(self, func):
        # invoking the func at init time causes syncdb to croak
        self.cached_object = None
        self.func = func

    def __call__(self, refresh=False):
        if self.cached_object is None or refresh:
            self.cached_object = self.func()
        return self.cached_object


def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    return type('Enum', (), enums)
