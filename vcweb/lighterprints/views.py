from datetime import datetime, timedelta
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import escape
from django.utils.timesince import timesince
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import BaseDetailView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core.middleware import detect_mobile

from vcweb.core import unicodecsv
from vcweb.core.decorators import participant_required
from vcweb.core.forms import (ChatForm, LoginForm, CommentForm, LikeForm, ParticipantGroupIdForm, GeoCheckinForm)
from vcweb.core.models import (ChatMessage, Comment, Experiment, ParticipantGroupRelationship, ParticipantRoundDataValue, Like)
from vcweb.core.services import foursquare_venue_search
from vcweb.core.views import JSONResponseMixin, DataExportMixin, dumps, set_authentication_token, json_response
from vcweb.lighterprints.forms import ActivityForm
from vcweb.lighterprints.models import (Activity, get_all_activities_tuple, do_activity,
        get_lighterprints_experiment_metadata, get_lighterprints_public_experiment, get_activity_performed_parameter,
        points_to_next_level, get_group_score, get_footprint_level, get_foursquare_category_ids,
        get_unlocked_activities, get_available_activities, get_activity_performed_counts)

from collections import defaultdict
import itertools
import logging
#import tempfile
logger = logging.getLogger(__name__)

class ActivityListView(JSONResponseMixin, MultipleObjectTemplateResponseMixin, BaseListView):
    model = Activity

    def get_context_data(self, **kwargs):
        context = super(ActivityListView, self).get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated():
            # authenticated request, figure out if this activity is available
            participant_group_id = self.request.GET.get('participant_group_id')
            if not participant_group_id:
                raise Http404
            participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related(depth=2), pk=participant_group_id)
            # XXX: we can only return a context dictionary or raise an exception
            # at this location
            if participant_group_relationship.participant != user.participant:
                logger.warning("authenticated user %s tried to retrieve activity listing for %s", user, participant_group_relationship)
                context['success'] = False
                context['flattened_activities'] = []
                return context
            all_activities = context['activity_list']
            (flattened_activities, activity_by_level) = get_all_activities_tuple(participant_group_relationship, all_activities)
            context['activity_by_level'] = dict(activity_by_level)
            context['flattened_activities'] = flattened_activities
            return context
        raise PermissionDenied("You must be authenticated to view all activities.")

    def render_to_response(self, context, **response_kwargs):
        output_format = self.kwargs['format']
        if output_format and output_format.endswith('json'):
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
        self.participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related(depth=1), pk=participant_group_id)
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

# FIXME: use persistent_messages instead where the user has to explicitly clear /
# dismiss the messages.  additional fields would be target_id
def get_notification_json(participant_group_relationship):
# FIXME: push into ParticipantGroupRelationship
    notification_date = participant_group_relationship.notifications_since
    if notification_date is None:
        notification_date = participant_group_relationship.date_created
    logger.debug("Finding notifications for participant %s since %s", participant_group_relationship, notification_date)
    json_array = []
# selects only comments and likes whose targeted action belongs to the participant_group_relationship in
# question and that have been posted since the last user's login
    user_actions = itertools.chain(*[cls.objects.filter(target_data_value__participant_group_relationship=participant_group_relationship,
        last_modified__gte=notification_date).exclude(participant_group_relationship=participant_group_relationship) for cls in (Comment, Like)])
    # bah, need to use django-model-utils InheritanceManager to properly downcast and get access to the appropriate
    # subtype to_dict() method
    for user_action in user_actions:
        user_action_dict = user_action.to_dict()
        target_data_value = user_action.target_data_value
        target_value = target_data_value.value
        if target_data_value.parameter == get_activity_performed_parameter():
            target_value = target_data_value.value.display_name
        user_action_dict['target_pk'] = target_data_value.pk
        user_action_dict['target_value'] = target_value
        user_action_dict['target_type'] = target_data_value.parameter.name
        user_action_dict['summary_type'] = user_action.parameter.name
        json_array.append(user_action_dict)
    logger.debug("returning notifications %s for participant %s", json_array, participant_group_relationship)
    return dumps({'success': True, 'notifications': json_array})

@login_required
def get_notifications(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        notifications = get_notification_json(participant_group_relationship)
        return json_response(request, notifications)
    else:
        logger.warning("authenticated user %s tried to retrieve notifications for %s", request.user,
                participant_group_relationship)
        return HttpResponse(dumps({'success':False, 'message': 'Invalid authz request'}))

@login_required
def update_notifications_since(request):
    form = ParticipantGroupIdForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        if request.user.participant == participant_group_relationship.participant:
            participant_group_relationship.notifications_since = datetime.now()
            participant_group_relationship.save()
            return HttpResponse(dumps({'success':True}))
        else:
            logger.warning("authenticated user %s tried to update notifications since for %s", request.user, participant_group_relationship)
    return HttpResponse(dumps({'success':False, 'message': 'Invalid request'}))
'''
[(4, u'adjust-thermostat'),
 (2, u'eat-local-lunch'),
  (1, u'enable-sleep-on-computer'),
   (5, u'recycle-materials'),
    (3, u'share-your-ride'),
     (10, u'bike-or-walk'),
      (7, u'computer-off-night'),
       (9, u'no-beef'),
        (8, u'recycle-paper'),
         (14, u'air-dry-clothes'),
          (15, u'cold-water-wash'),
           (13, u'eat-green-lunch'),
            (11, u'lights-off'),
             (12, u'vegan-for-a-day')]
             '''
@login_required
def activity_performed_counts(request, participant_group_id):
    _activity_ids = (8, 3, 1, 9, 4, 15, 2, 5, 10, 7, 12, 11, 14, 13)
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        activity_performed_counts = get_activity_performed_counts(participant_group_relationship)
        activity_counts_dict = defaultdict(int, [(d['int_value'], d['count']) for d in activity_performed_counts])
        activity_counts = [activity_counts_dict[activity_id] for activity_id in _activity_ids]
        logger.debug("activity counts: %s", activity_counts)
        return HttpResponse(dumps({'success': True, 'activity_counts': activity_counts}))
    return HttpResponse(dumps({'success':False, 'message': 'Invalid request'}))

@login_required
def group_score(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group'), pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        group = participant_group_relationship.group
        (average_points, total_points) = get_group_score(group)
        logger.debug("getting group score for: %s", group)
        level = get_footprint_level(group)
        groups = []
        groups.append({
            'level': level,
            'average_points_per_person': average_points,
            'total_points': total_points,
            'points_to_next_level': points_to_next_level(level)
            })
        return HttpResponse(dumps({'success':True, 'scores': groups }))
    return HttpResponse(dumps({'success':False, 'message': 'Invalid request'}))

@login_required
def group_activity(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related(depth=1), pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        content = get_group_activity_json(participant_group_relationship)
        return json_response(request, content)
    else:
        logger.warning("authenticated user %s tried to retrieve group activity for %s", request.user, participant_group_relationship)
        return HttpResponse(dumps({'success': False, 'message': 'Invalid authz request'}))

def get_group_activity_json(participant_group_relationship, number_of_activities=10, retrieve_all=True):
    group = participant_group_relationship.group
    chat_messages = []
    for chat_message in ChatMessage.objects.filter(participant_group_relationship__group=group).order_by('-date_created'):
        pgr = chat_message.participant_group_relationship
        comments = [c.to_dict() for c in Comment.objects.filter(target_data_value=chat_message.pk)]
        likes = [like.to_dict() for like in Like.objects.filter(target_data_value=chat_message.pk)]
        chat_messages.append({
            'pk': chat_message.pk,
            'date_created': timesince(chat_message.date_created),
            'message': escape(chat_message.value),
            'participant_name': escape(pgr.participant.full_name),
            'participant_number': pgr.participant_number,
            'participant_group_id':pgr.pk,
            'comments': comments,
            'likes': likes
            })
    group_activity = []
    performed_activities = ParticipantRoundDataValue.objects.filter(participant_group_relationship__group=group,
            submitted=True, parameter=get_activity_performed_parameter()).order_by('-date_created')
    if retrieve_all:
        number_of_activities = len(performed_activities)
    for activity_prdv in performed_activities[:number_of_activities]:
        activity = activity_prdv.value
        activity_performed_dict = activity.to_dict(attrs=('display_name', 'name', 'icon_url', 'savings', 'points'))
        activity_performed_dict['date_performed'] = activity_prdv.date_created
        pgr = activity_prdv.participant_group_relationship
        activity_performed_dict['participant_number'] = pgr.participant_number
        activity_performed_dict['participant_name'] = pgr.participant.full_name
        activity_performed_dict['participant_group_id'] = pgr.pk
        activity_performed_dict['activity_performed_id'] = activity_prdv.pk
        activity_performed_dict['comments'] = [c.to_dict() for c in Comment.objects.filter(target_data_value=activity_prdv.pk)]
        activity_performed_dict['likes'] = [like.to_dict() for like in Like.objects.filter(target_data_value=activity_prdv.pk)]
        group_activity.append(activity_performed_dict)
    return dumps({
        'success': True,
        'chat_messages': chat_messages,
        'recent_activity': group_activity
        })

@csrf_exempt
@login_required
def perform_activity(request):
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        latitude = form.cleaned_data['latitude']
        longitude = form.cleaned_data['longitude']
        if participant_group_relationship.participant == request.user.participant:
            activity = get_object_or_404(Activity, pk=activity_id)
            performed_activity = do_activity(activity=activity, participant_group_relationship=participant_group_relationship)
# perform checkin logic here, query foursquare API for nearest "green" venu
            logger.debug("searching venues at %s,%s", latitude, longitude)
            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
                    categoryId=','.join(get_foursquare_category_ids()))
            logger.debug("Found venues: %s", venues)
            if performed_activity is not None:
                activity_dict = activity.to_dict()
                activity_dict['date_created'] = performed_activity.date_created
                activity_dict['performed_activity_id'] = performed_activity.pk
                activity_dict['success'] = True
                return HttpResponse(dumps(activity_dict), content_type='application/json')
        else:
            logger.warning("authenticated user %s tried to perform activity %s as %s", request.user, activity_id, participant_group_relationship)
    return HttpResponse(dumps({'success': False, 'response': "Could not perform activity"}), content_type='application/json')

@csrf_exempt
@login_required
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post message %s as %s", request.user, message, participant_group_relationship)
            return HttpResponse(dumps({'success': False, 'message': "Invalid request"}))
        chat_message_parameters = {
                'value': message,
                'participant_group_relationship': participant_group_relationship
                }
        logger.debug("about to check target participant")
# FIXME: causing errors, need to check logic
#        if 'target_participant_group_id' in form.cleaned_data:
#            target_participant_group_id = form.cleaned_data['target_participant_group_id']
#            target_participant = ParticipantGroupRelationship.objects.get(pk=target_participant_group_id)
#            chat_message_parameters['target_participant'] = target_participant
        logger.debug("creating chat message")
        chat_message = ChatMessage.objects.create(**chat_message_parameters)
        logger.debug("Participant %s created chat message %s", participant_group_relationship.participant, chat_message)
        content = get_group_activity_json(participant_group_relationship)
        return HttpResponse(content, content_type='application/json')
    return HttpResponse(dumps({'success': False, 'message': "Invalid chat message post"}))


@csrf_exempt
@login_required
def like(request):
    form = LikeForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to like target_id %s as %s", request.user, target_id, participant_group_relationship)
            return HttpResponse(dumps({'success': False, 'message': "Invalid request"}))
        logger.debug("pgr: %s", participant_group_relationship)
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        logger.debug("target: %s", target)
        # FIXME: either needs a uniqueness constraint to ensure that duplicates don't get created or add guards when we
        # retrieve them to only send back the latest one (feels hacky).  See
        # https://bitbucket.org/virtualcommons/vcweb/issue/59/get_or_create-issues-for-likes
        Like.objects.create(participant_group_relationship=participant_group_relationship, target_data_value=target)
        logger.debug("Participant %s liked %s", participant_group_relationship, target)
        return HttpResponse(dumps({'success': True}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return HttpResponse(dumps({'success': False, 'message': 'Invalid post comment'}))


@csrf_exempt
@login_required
def post_comment(request):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post comment %s on target %s as %s", request.user, message, target_id, participant_group_relationship)
            return HttpResponse(dumps({'success': False, 'message': "Invalid request"}))
        logger.debug("pgr: %s", participant_group_relationship)
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        logger.debug("target: %s", target)
        comment = Comment.objects.create(
                value=message,
                participant_group_relationship=participant_group_relationship,
                target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s", participant_group_relationship.participant, message, target)

        #content = get_group_activity_json(participant_group_relationship)
        #return HttpResponse(content, content_type='application/json')
        return HttpResponse(dumps({'success': True, 'comment' : escape(comment.value), 'target': target}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return HttpResponse(dumps({'success': False, 'message': 'Invalid post comment'}))

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
            if not active_experiments:
                logger.debug("No experiments available for user: %s", user)
                return HttpResponse(dumps({ 'success': False, 'message': 'No experiments available' }), content_type='application/json')
# FIXME: defaulting to first active experiment... need to revisit this.
            active_experiment = active_experiments[0]
            participant_group_relationship = participant.get_participant_group_relationship(active_experiment)
            return HttpResponse(dumps({'success': True, 'participant_group_id': participant_group_relationship.id}), content_type='application/json')
        else:
            logger.debug("invalid form %s", form)
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return HttpResponse(dumps({'success': False, 'message': "Invalid login"}), content_type='application/json')

class CsvExportView(DataExportMixin, BaseDetailView):
    def export_data(self, response, experiment):
        logger.debug("exporting data for %s", experiment)
        writer = unicodecsv.UnicodeWriter(response)
        experiment_start_time = experiment.current_round_start_time
        today = datetime.today()
        start = today.date()
        end = today
        writer.writerow(['Interval Start', 'Interval End', 'Group', 'Total Points', 'Average Points', '# Members'])
        while start > experiment_start_time.date():
            for group in experiment.group_set.all():
                (average, total) = get_group_score(group, start=start, end=end)
                writer.writerow([start, end, group, total, average, group.size])
            end = start
            start = start - timedelta(1)
        writer.writerow(['Interval Start', 'Interval End', 'Participant', 'Activity', 'Points', 'Date created'])
        start = today.date()
        end = today
        while start > experiment_start_time.date():
            prdvs = ParticipantRoundDataValue.objects.filter(round_data__experiment=experiment, date_created__range=(start, end))
            for prdv in prdvs.filter(parameter=get_activity_performed_parameter()).order_by('-date_created'):
                writer.writerow([start, end, prdv.participant_group_relationship, prdv.value, prdv.value.points, prdv.date_created])
            end = start
            start = start - timedelta(1)
        # write out participant summary
        writer.writerow(['Participant', 'Total Points'])
        for participant_group_relationship in experiment.participant_group_relationships:
            performed_activities = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter())
            total_points = 0
            for performed_activity in performed_activities:
                total_points += performed_activity.value.points
            writer.writerow([participant_group_relationship, total_points])


@participant_required
def participate(request, experiment_id=None):
    detect_mobile(request)
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    pgr = participant.get_participant_group_relationship(experiment)
    all_activities = Activity.objects.all()
    activities = get_available_activities(pgr)
    group_level = get_footprint_level(pgr.group)
    (average_points, total_points) = get_group_score(pgr.group)
    points_needed = points_to_next_level(group_level)
    if request.mobile:
        # FIXME: change this to look up templates in a mobile templates directory?
        return redirect('https://vcweb.asu.edu/lfpdev')
    return render(request, 'lighterprints/participate.html', {
        'experiment': experiment, 'activities': activities, 'all_activities':all_activities, 'participant_group_relationship': pgr,
        'group_level': group_level,
        'total_points': total_points,
        'average_points': average_points,
        'points_to_next_level': points_needed,
        })

@participant_required
def group_view(request, experiment_id=None):
    detect_mobile(request)
    participant = request.user.participant
    if experiment_id is None:
        experiment = get_lighterprints_public_experiment()
        pgr = experiment.add_participant(participant)
    else:
        experiment = get_object_or_404(Experiment, pk=experiment_id)
        pgr = participant.get_participant_group_relationship(experiment)
    return render(request, 'lighterprints/group.html', {'experiment': experiment})

def checkin(request):
    form = GeoCheckinForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        latitude = form.cleaned_data['latitude']
        longitude = form.cleaned_data['longitude']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        logger.debug("%s checking at at (%s, %s)", participant_group_relationship, latitude, longitude)
        if request.user.participant == participant_group_relationship.participant:
# perform checkin logic here, query foursquare API for nearest "green" venu
            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
                    categoryId=','.join(get_foursquare_category_ids()))
            logger.debug("Found venues: %s", venues)
            return HttpResponse(dumps({'success':True}))
        else:
            logger.warning("authenticated user %s tried to checkin at (%s, %s) for %s", request.user, latitude, longitude, participant_group_relationship)
    return HttpResponse(dumps({'success':False, 'message': 'Invalid request'}))
