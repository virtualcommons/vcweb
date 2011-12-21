from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.timesince import timesince
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import BaseDetailView
from django.views.generic.edit import FormView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core.forms import ChatForm, LoginForm, CommentForm
from vcweb.core.models import (ChatMessage, ParticipantGroupRelationship, ParticipantRoundDataValue)
from vcweb.core.views import JSONResponseMixin, dumps, set_authentication_token, json_response
from vcweb.lighterprints.forms import ActivityForm
from vcweb.lighterprints.models import (Activity, to_activity_dict, get_all_available_activities, do_activity, get_lighterprints_experiment_metadata, get_activity_performed_parameter)

import collections
import logging
logger = logging.getLogger(__name__)

class ActivityListView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
    model = Activity

    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        all_activities = context['activity_list']
        if self.request.user.is_authenticated():
            # authenticated request, figure out if this activity is available
            participant_group_id = self.request.GET.get('participant_group_id')
            participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
            (flattened_activities, activity_by_level) = get_all_available_activities(participant_group_relationship, all_activities)
            context['activity_by_level'] = dict(activity_by_level)
            context['flattened_activities'] = flattened_activities
            return context
        raise PermissionDenied("You must be authenticated to view all activities.")

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'json':
            return JSONResponseMixin.render_to_response(self, context, context_key='flattened_activities')
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

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

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get('format', 'html') == 'json':
            return JSONResponseMixin.render_to_response(self, context, context_key='group_activity')
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(DiscussionBoardView, self).get_context_data(**kwargs)
        context['group'] = self.group
        context['participant_group_relationship'] = self.participant_group_relationship
        context['group_activity'] = get_group_activity_json(self.participant_group_relationship)
        return context


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

def group_activity(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
    content = get_group_activity_json(participant_group_relationship)
    return json_response(request, content)

def get_group_activity_json(participant_group_relationship, number_of_activities=5, retrieve_all=True):
    group = participant_group_relationship.group
    chat_messages = []
    for chat_message in ChatMessage.objects.filter(participant_group_relationship__group=group).order_by('-date_created'):
        pgr = chat_message.participant_group_relationship
        chat_messages.append({
            'date_created': timesince(chat_message.date_created),
            'message': chat_message.message,
            'participant_number': pgr.participant_number,
            'participant_group_id':pgr.pk
            })
    group_activity = []
    performed_activities = ParticipantRoundDataValue.objects.filter(participant_group_relationship__group=group, submitted=True, parameter=get_activity_performed_parameter()).order_by('-date_created')
    if retrieve_all:
        number_of_activities = len(performed_activities)
    for activity_prdv in performed_activities[:number_of_activities]:
        # FIXME: change this to activity name if we decide to use names instead of
        # pks
        activity = Activity.objects.get(pk=activity_prdv.value)
        performed_activity_dict = to_activity_dict(activity, attrs=('pk', 'display_name', 'name', 'icon_url', 'savings'))
        performed_activity_dict['date_performed'] = activity_prdv.date_created
        pgr = activity_prdv.participant_group_relationship
        performed_activity_dict['participant_number'] = pgr.participant_number
        performed_activity_dict['participant_group_id'] = pgr.pk
        performed_activity_dict['performed_activity_id'] = activity_prdv.pk
        group_activity.append(performed_activity_dict)
    return dumps({
        'chat_messages': chat_messages,
        'recent_activity': group_activity
        })

@csrf_exempt
def perform_activity(request):
    logger.debug("performing activity")
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        activity = get_object_or_404(Activity, pk=activity_id)
        performed_activity = do_activity(activity=activity, participant_group_relationship=participant_group_relationship)
        if performed_activity is not None:
            activity_dict = to_activity_dict(activity)
            activity_dict['date_created'] = performed_activity.date_created
            activity_dict['performed_activity_id'] = performed_activity.pk
            return HttpResponse(dumps(activity_dict), content_type='application/json')
    return HttpResponseBadRequest(dumps({'response': "Could not perform activity"}), content_type='application/json')

@csrf_exempt
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        chat_message = participant_group_relationship.participant_chat_message_set.create(message=message,
                round_data=participant_group_relationship.current_round_data)
        logger.debug("Participant %s created chat message %s", participant_group_relationship.participant, chat_message)
        content = get_group_activity_json(participant_group_relationship)
        return HttpResponse(content, content_type='application/json')
    return HttpResponseBadRequest(dumps({'response': "Invalid chat message post"}))

@csrf_exempt
def post_comment(request):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        comment = participant_group_relationship.comment_set.create(text=message,
                round_data=participant_group_relationship.current_round_data,
                target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s", participant_group_relationship.participant, message, target)

        #content = get_group_activity_json(participant_group_relationship)
        #return HttpResponse(content, content_type='application/json')
        return HttpResponse(dumps({'comment' : comment}))
    return HttpResponseBadRequest(dumps({'response': 'Invalid comment post'}))

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
            return HttpResponse(dumps({'success': True, 'participant_group_id': participant_group_relationship.id}), content_type='application/json')
        else:
            logger.debug("invalid form %s", form)
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return HttpResponse(dumps({'success': False, 'message': "Invalid login"}), content_type='application/json')
