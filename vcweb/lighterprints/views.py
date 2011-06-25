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
        context['activity_by_level'] = self.get_activity_by_level()
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'json':
            return JSONResponseMixin.render_to_response(self, context, context_key='activity_by_level')
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

class ActivityDetailView(JSONResponseMixin, BaseDetailView):
    template_name = 'lighterprints/activity_detail.html'

class MobileView(ActivityListView):
    jqm_grid_columns = tuple("abcde")

    def get_activity_by_level(self):
        activity_by_level = collections.defaultdict(list)
        for index, activity in enumerate(Activity.objects.all()):
            activity_by_level[activity.level].append((activity, MobileView.jqm_grid_columns[index]))
        return dict(activity_by_level)

    def get_context_data(self, **kwargs):
        context = super(MobileView, self).get_context_data(**kwargs)
        available_activities = get_available_activities(self.request)
        context['grid_letter'] = MobileView.jqm_grid_columns[max(len(available_activities) - 2, 0)]
        context['available_activities'] = available_activities
        return context

    def get_template_names(self):
        return ['lighterprints/mobile/index.html']

class DoActivityView(FormView):
    pass

def get_available_activities(request):
    # FIXME: currently stubbed out to return all activities. should move this to
    # models.py and have it take a Participant?
    return zip(Activity.objects.all(), MobileView.jqm_grid_columns)


