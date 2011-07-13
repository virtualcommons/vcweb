from django.shortcuts import get_object_or_404
from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import FormView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core.models import ParticipantGroupRelationship, ChatMessage
from vcweb.core.views import JSONResponseMixin
# FIXME: move to core?
from vcweb.lighterprints.forms import ChatForm
from vcweb.lighterprints.models import Activity

import collections
import logging
logger = logging.getLogger(__name__)


class ActivityListView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
# FIXME: replace with dynamic set
    model = Activity

    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        all_activities = context['activity_list']
        activity_by_level = collections.defaultdict(list)
        flattened_activities = []
        for activity in all_activities:
            activity_by_level[activity.level].append(activity)
            #activity_as_dict = collections.OrderedDict()
            activity_as_dict = {}
            for attr_name in ('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'group_activity', 'icon_url', 'time_remaining'):
                activity_as_dict[attr_name] = getattr(activity, attr_name, None)
            flattened_activities.append(activity_as_dict)

        context['activity_by_level'] = dict(activity_by_level)
        context['flattened_activities'] = flattened_activities
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'json':
            return JSONResponseMixin.render_to_response(self, context, context_key='flattened_activities')
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

class ActivityDetailView(JSONResponseMixin, BaseDetailView):
    template_name = 'lighterprints/activity_detail.html'

class MobileView(ActivityListView):
    jqm_grid_columns = tuple("abcde")

    def get_context_data(self, **kwargs):
        context = super(MobileView, self).get_context_data(**kwargs)
        activity_by_level = collections.defaultdict(list)
        for index, activity in enumerate(context['activity_list']):
            activity_by_level[activity.level].append((activity,
                MobileView.jqm_grid_columns[index % 5]))
        context['activity_by_level'] = dict(activity_by_level)

        available_activities = get_available_activities(self.request)
        context['grid_letter'] = MobileView.jqm_grid_columns[max(len(available_activities) - 2, 0)]
        context['available_activities'] = available_activities
        return context

    def get_template_names(self):
        return ['lighterprints/mobile/index.html']

class DoActivityView(FormView):
    pass

class PostChatMessageView(FormView):
    form_class = ChatForm
    pass

class DiscussionBoardView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
    model = ChatMessage
    def get_queryset(self):
        # FIXME: stubbed out for now, passing in the participant id for the time
        # being
        # participant = self.request.user.participant
        participant_id = self.kwargs['participant_id']
        experiment_id = self.kwargs['experiment_id']
# FIXME: will change once we have proper auth set up
        self.participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, participant__pk=participant_id, group__experiment__pk=experiment_id)
        self.group = self.participant_group_relationship.group
        return ChatMessage.objects.filter(participant_group_relationship__group = self.group)

    def get_context_data(self, **kwargs):
        context = super(DiscussionBoardView, self).get_context_data(**kwargs)
        context['group'] = self.group
        context['participant_group_relationship'] = self.participant_group_relationship
        return context

def get_available_activities(request):
    # FIXME: currently stubbed out to return all activities. should move this to
    # models.py and have it take a Participant?
    return zip(Activity.objects.all(), MobileView.jqm_grid_columns)


