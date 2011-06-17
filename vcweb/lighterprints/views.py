from django import http
from django.db.models import Model
from django.db.models.query import QuerySet
from django.core.serializers import serialize
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin
from django.views.generic.detail import BaseDetailView
from django.utils.functional import curry
from django.utils.simplejson import dumps, loads, JSONEncoder

from vcweb.lighterprints.models import Activity

import collections
import logging
logger = logging.getLogger(__name__)

class DjangoJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, QuerySet):
            return loads(serialize('json', obj))
        elif isinstance(obj, Model):
            return loads(serialize('json', [obj]))[0]
        else:
            return JSONEncoder.default(self, obj)

dumps = curry(dumps, cls=DjangoJSONEncoder)

class JSONResponseMixin(object):
    def render_to_response(self, context, **kwargs):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context, **kwargs))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        logger.debug("return json response %s", content)
        return http.HttpResponse(content,
                content_type='application/json',
                **httpresponse_kwargs)

    def convert_context_to_json(self, context, context_key='object_list', **kwargs):
        "Convert the context dictionary into a JSON object"
        logger.debug("serializing context %s with context_key %s", context, context_key)
        return dumps(context[context_key])
#        return serializers.serialize('json', context[context_key])

class ActivityListView(JSONResponseMixin, BaseListView, MultipleObjectTemplateResponseMixin):
# FIXME: replace with dynamic set
    model = Activity

    def get_activity_by_level(self):
        activity_by_level = collections.defaultdict(list)
        for activity in Activity.objects.all():
            activity_by_level[activity.level].append(activity)
        return dict(activity_by_level)

    def get_context_data(self, **kwargs):
        context = super(BaseListView, self).get_context_data(**kwargs)
        logger.debug("context is %s", context)
        context['activity_by_level'] = self.get_activity_by_level()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'json':
            return JSONResponseMixin.render_to_response(self, context, context_key='activity_by_level')
        else:
            logger.debug("returning MOTRM render_to_response with context %s", context['activity_by_level'])
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

class ActivityDetailView(JSONResponseMixin, BaseDetailView):
    template_name = 'lighterprints/activity_detail.html'
