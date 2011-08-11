from django.contrib import auth
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import FormView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core.forms import LoginForm
from vcweb.core.models import (ChatMessage, Experiment, ParticipantGroupRelationship)
from vcweb.core.views import JSONResponseMixin, dumps, set_authentication_token
# FIXME: move ChatForm to core?
from vcweb.lighterprints.forms import ActivityForm, ChatForm
from vcweb.lighterprints.models import (Activity, is_activity_available, do_activity, get_lighterprints_experiment_metadata)

import collections
import logging
logger = logging.getLogger(__name__)


class ActivityListView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
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
            try:
                if self.request.user.is_authenticated():
                    # authenticated request, figure out if this activity is available
                    participant_group_id = self.request.GET.get('participant_group_id')
                    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
                    activity_as_dict['availability'] = is_activity_available(activity, participant_group_relationship)
            except Exception as e:
                logger.debug("failed to get authenticated activity list: %s", e)
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

def get_available_activities(request):
    # FIXME: currently stubbed out to return all activities. should move this to
    # models.py and have it take a Participant?
    return zip(Activity.objects.all(), MobileView.jqm_grid_columns)

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

@csrf_exempt
def perform_activity(request):
    logger.debug("performing activity")
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_pk = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_pk)
        activity = get_object_or_404(Activity, pk=activity_id)
        performed_activity = do_activity(activity=activity, participant_group_relationship=participant_group_relationship)
        if performed_activity is not None:
            return HttpResponse(dumps(performed_activity), content_type='text/javascript')
    return HttpResponseBadRequest(dumps({'response': "Could not perform activity"}), content_type='text/javascript')

@csrf_exempt
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_pk = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_pk)
        group = participant_group_relationship.group
        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                message=message, round_data=group.current_round_data)
        logger.debug("Participant %s created chat message %s", request.user.participant, chat_message)
        content = dumps(ChatMessage.objects.filter(participant_group_relationship__group=group))
        return HttpResponse(content, content_type='text/javascript')
    return HttpResponseBadRequest(dumps({'response': "Invalid chat message post"}))

class DiscussionBoardView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
    model = ChatMessage
    template_name = 'discussion_board.html'
    def get_queryset(self):
        # FIXME: stubbed out for now, passing in the participant id for the time
        # being
        # participant = self.request.user.participant
        participant_group_id = self.kwargs['participant_group_id']
# FIXME: will change once we have proper auth set up
        self.participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        self.group = self.participant_group_relationship.group
        return ChatMessage.objects.filter(participant_group_relationship__group = self.group)

    def get_context_data(self, **kwargs):
        context = super(DiscussionBoardView, self).get_context_data(**kwargs)
        context['group'] = self.group
        context['participant_group_relationship'] = self.participant_group_relationship
        return context

@csrf_exempt
def login(request):
    form = LoginForm(request.POST or None)
    try:
        if form.is_valid():
            user = form.user_cache
            logger.debug("user was authenticated as %s, attempting to login", user)
            auth.login(request, user)
            set_authentication_token(user, request.session.session_key)
            participant = user.participant
            active_experiments = participant.experiments.filter(status__in=('ACTIVE', 'ROUND_IN_PROGRESS'), experiment_metadata=get_lighterprints_experiment_metadata())
            # FIXME: assuming participant is only participating in one active experiment
            # at a time..
            active_experiment = active_experiments[0]
            participant_group_relationship = participant.get_participant_group_relationship(active_experiment)
            return HttpResponse(dumps({'participant_group_id': participant_group_relationship.id}), content_type='text/javascript')
        else:
            logger.debug("invalid form %s", form)
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return HttpResponseBadRequest(dumps({"response": "Invalid login"}), content_type='text/javascript')
