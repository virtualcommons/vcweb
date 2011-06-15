from django import http
from django.core import serializers
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin
from django.views.generic.detail import BaseDetailView

from vcweb.lighterprints.models import Activity

import logging
logger = logging.getLogger(__name__)

class JSONResponseMixin(object):
    def render_to_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        logger.debug("return json response %s", content)
        return http.HttpResponse(content,
                content_type='application/json',
                **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        logger.debug("serializing context %s", context)
        return serializers.serialize('json', context['object_list'], fields=('display_name', 'description', 'url'))

class ActivityListView(JSONResponseMixin, BaseListView, MultipleObjectTemplateResponseMixin):
# FIXME: replace with dynamic set
    model = Activity
    def render_to_response(self, context):
        if self.request.GET.get('format', 'html') == 'json':
            logger.debug("returning json response")
            return JSONResponseMixin.render_to_response(self, context)
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)


class ActivityDetailView(JSONResponseMixin, BaseDetailView):
    template_name = 'lighterprints/activity_detail.html'
