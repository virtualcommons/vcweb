from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.db.models.query import QuerySet
from django.utils.functional import curry
from django.utils.simplejson import loads, dumps

class VcwebJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, QuerySet):
            return loads(serialize('json', obj))
        elif isinstance(obj, Model):
            return loads(serialize('json', [obj]))[0]
        else:
            return DjangoJSONEncoder.default(self, obj)

dumps = curry(dumps, cls=VcwebJSONEncoder)
