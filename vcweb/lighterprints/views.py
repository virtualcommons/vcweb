from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import FormView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core.views import JSONResponseMixin
from vcweb.lighterprints.models import Activity

import collections
import logging
logger = logging.getLogger(__name__)


class ActivityListView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
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
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

class ActivityDetailView(JSONResponseMixin, BaseDetailView):
    template_name = 'lighterprints/activity_detail.html'

class DoActivityView(FormView):
    pass

class MobileView(ActivityListView):

    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        activity_by_level = collections.defaultdict(list)
        jquery_grid_list = list("abcde")
        for index, activity in enumerate(Activity.objects.all()):
            activity_by_level[activity.level].append((activity, jquery_grid_list[index]))
        context['activity_by_level'] = dict(activity_by_level)
        logger.debug("activity by level %s", activity_by_level)
        return context

    def get_template_names(self):
        return ['lighterprints/mobile.html']
