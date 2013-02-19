from datetime import datetime, timedelta
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.detail import DetailView, BaseDetailView
from django.views.generic.list import BaseListView, MultipleObjectTemplateResponseMixin

from vcweb.core import unicodecsv
from vcweb.core.decorators import participant_required
from vcweb.core.forms import (ChatForm, LoginForm, CommentForm, LikeForm, ParticipantGroupIdForm, GeoCheckinForm)
from vcweb.core.http import JsonResponse
from vcweb.core.models import (ChatMessage, Comment, Experiment, ParticipantGroupRelationship, ParticipantRoundDataValue, Like)
from vcweb.core.services import foursquare_venue_search
from vcweb.core.views import JSONResponseMixin, DataExportMixin, dumps, set_authentication_token, json_response, get_active_experiment
from vcweb.lighterprints.forms import ActivityForm
from vcweb.lighterprints.models import (Activity, get_all_activities_tuple, do_activity, get_group_activity,
        get_treatment_type, get_lighterprints_experiment_metadata,
        get_activity_performed_parameter, get_points_to_next_level, get_group_score, get_footprint_level,
        get_foursquare_category_ids, get_activity_performed_counts, get_time_remaining)

from collections import defaultdict
from operator import itemgetter
import itertools
import logging
#import tempfile
logger = logging.getLogger(__name__)

# FIXME: these are now mostly defunct, remove when not needed
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
            participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group'), pk=participant_group_id)
            # XXX: we can only return a context dictionary or raise an exception
            # at this location
            if participant_group_relationship.participant != user.participant:
                logger.warning("authenticated user %s tried to retrieve activity listing for %s", user, participant_group_relationship)
                context['success'] = False
                context['flattened_activities'] = []
                return context
            all_activities = context['activity_list']
            (flattened_activities, level_activity_list) = get_all_activities_tuple(participant_group_relationship, all_activities)
            context['activity_by_level'] = level_activity_list
            context['flattened_activities'] = flattened_activities
            return context
        raise PermissionDenied("You must be authenticated to view all activities.")

    def render_to_response(self, context, **response_kwargs):
        output_format = self.kwargs['format']
        if output_format and output_format.endswith('json'):
            return JSONResponseMixin.render_to_response(self, context, context_key='flattened_activities')
        else:
            return MultipleObjectTemplateResponseMixin.render_to_response(self, context)

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
        return JsonResponse(dumps({'success':False, 'message': 'Invalid authz request'}))

@login_required
def update_notifications_since(request):
    form = ParticipantGroupIdForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship, pk=participant_group_id)
        if request.user.participant == participant_group_relationship.participant:
            participant_group_relationship.notifications_since = datetime.now()
            participant_group_relationship.save()
            return JsonResponse(dumps({'success':True}))
        else:
            logger.warning("authenticated user %s tried to update notifications since for %s", request.user, participant_group_relationship)
    return JsonResponse(dumps({'success':False, 'message': 'Invalid request'}))
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
        return JsonResponse(dumps({'success': True, 'activity_counts': activity_counts}))
    return JsonResponse(dumps({'success':False, 'message': 'Invalid request'}))

@login_required
def group_score(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group'), pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        group = participant_group_relationship.group
        (average_points, total_points, total_participant_points) = get_group_score(group, participant_group_relationship=participant_group_relationship)
        level = get_footprint_level(group)
        groups = []
        groups.append({
            'level': level,
            'average_points_per_person': average_points,
            'total_points': total_points,
            'total_participant_points': total_participant_points,
            'points_to_next_level': get_points_to_next_level(level)
            })
        return JsonResponse(dumps({'success':True, 'scores': groups }))
    return JsonResponse(dumps({'success':False, 'message': 'Invalid request'}))

@login_required
def group_activity(request, participant_group_id):
    participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group__experiment'), pk=participant_group_id)
    if request.user.participant == participant_group_relationship.participant:
        content = get_view_model_json(participant_group_relationship)
        return json_response(request, content)
    else:
        logger.warning("authenticated user %s tried to retrieve group activity for %s", request.user, participant_group_relationship)
        return JsonResponse(dumps({'success': False, 'message': 'Invalid authz request'}))

@csrf_exempt
@participant_required
def perform_activity(request):
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user'), pk=participant_group_id)
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
                return JsonResponse(dumps({
                    'success': True,
                    'viewModel':get_view_model_json(participant_group_relationship)
                    }))
        else:
            logger.warning("authenticated user %s tried to perform activity %s as %s", request.user, activity_id, participant_group_relationship)
    return JsonResponse(dumps({'success': False, 'response': "Could not perform activity"}))

@csrf_exempt
@login_required
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user'), pk=participant_group_id)
        if pgr.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post message %s as %s", request.user, message, pgr)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        chat_message = ChatMessage.objects.create(value=message, participant_group_relationship=pgr)
        logger.debug("%s: %s", pgr.participant, chat_message)
# FIXME: just get the chat messages
        (team_activity, chat_messages) = get_group_activity(pgr)
        return JsonResponse(dumps({'success': True, 'viewModel': { 'groupActivity': team_activity } }))
    return JsonResponse(dumps({'success': False, 'message': "Invalid chat message post"}))


@csrf_exempt
@login_required
def like(request):
    form = LikeForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to like target_id %s as %s", request.user, target_id, participant_group_relationship)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        logger.debug("pgr: %s", participant_group_relationship)
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        logger.debug("target: %s", target)
        # FIXME: either needs a uniqueness constraint to ensure that duplicates don't get created or add guards when we
        # retrieve them to only send back the latest one (feels hacky).  See
        # https://bitbucket.org/virtualcommons/vcweb/issue/59/get_or_create-issues-for-likes
        round_data = participant_group_relationship.current_round_data
        Like.objects.create(round_data=round_data, participant_group_relationship=participant_group_relationship, target_data_value=target)
        logger.debug("Participant %s liked %s", participant_group_relationship, target)
        return JsonResponse(dumps({'success': True, 'viewModel': get_view_model_json(participant_group_relationship)}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse(dumps({'success': False, 'message': 'Invalid like post'}))

@csrf_exempt
@login_required
def post_comment(request):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post comment %s on target %s as %s", request.user, message, target_id, participant_group_relationship)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        logger.debug("%s commented on %s", participant_group_relationship, target)
        comment = Comment.objects.create(
                value=message,
                round_data=participant_group_relationship.round_data,
                participant_group_relationship=participant_group_relationship,
                target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s", participant_group_relationship.participant, message, target)
        return JsonResponse(dumps({'success': True, 'viewModel' : get_view_model_json(participant_group_relationship)}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse(dumps({'success': False, 'message': 'Invalid post comment'}))

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
# FIXME: defaulting to first active experiment... need to revisit this.
            active_experiment = get_active_experiment(participant, experiment_metadata=get_lighterprints_experiment_metadata())
            participant_group_relationship = participant.get_participant_group_relationship(active_experiment)
            return JsonResponse(dumps({'success': True, 'participant_group_id': participant_group_relationship.id}))
        else:
            logger.debug("invalid form %s", form)
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return JsonResponse(dumps({'success': False, 'message': "Invalid login"}))

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
                (average, total, total_participant_points) = get_group_score(group, start=start, end=end)
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

def get_view_model_json(participant_group_relationship, activities=None, experiment=None):
    if activities is None:
        activities = Activity.objects.all()
    own_group = participant_group_relationship.group
    if experiment is None:
        experiment = own_group.experiment
    round_data = experiment.current_round_data
    round_configuration = round_data.round_configuration
    treatment_type = get_treatment_type(own_group, round_configuration=round_configuration)
    group_data = []
    for group in experiment.group_set.all():
        (average_points, total_points, total_participant_points) = get_group_score(group, participant_group_relationship=participant_group_relationship, round_data=round_data)
        group_level = get_footprint_level(group, round_data=round_data)
        points_to_next_level = get_points_to_next_level(group_level)
        if group == own_group:
            own_group_level = group_level
            own_average_points = average_points
            own_points_to_next_level = points_to_next_level
        group_data.append({
            'groupName': group.name,
            'groupLevel': group_level,
            'groupSize': group.size,
            'averagePoints': average_points,
            'totalPoints': total_points,
            'totalParticipantPoints': total_participant_points,
            'pointsToNextLevel': points_to_next_level
            })
    group_data.sort(key=itemgetter('averagePoints'), reverse=True)
    (activity_dict_list, level_activity_list) = get_all_activities_tuple(participant_group_relationship, activities, group_level=own_group_level)
    (team_activity, chat_messages) = get_group_activity(participant_group_relationship)
    #(chat_messages, group_activity) = get_group_activity_tuple(participant_group_relationship)
    (hours_left, minutes_left) = get_time_remaining()
    first_visit = participant_group_relationship.first_visit
    if first_visit:
        participant_group_relationship.first_visit = False
        participant_group_relationship.save()
    return dumps({
        'participantGroupId': participant_group_relationship.pk,
        'groupData': group_data,
        'hoursLeft': hours_left,
        'minutesLeft': minutes_left,
        'firstVisit': first_visit,
        'groupLevel': own_group_level,
        'averagePoints': own_average_points,
        'pointsToNextLevel': own_points_to_next_level,
        'groupActivity': team_activity,
        'groupName': own_group.name,
        'activities': activity_dict_list,
        'activitiesByLevel': level_activity_list,
        })

@participant_required
def get_view_model(request, participant_group_id=None):
    if participant_group_id is None:
        # check in the request query parameters as well
        participant_group_id = request.GET.get('participant_group_id')
# FIXME: replace with ParticipantGroupRelationship.objects.fetch(pk=participant_group_id)
    pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
    if pgr.participant != request.user.participant:
        # security check to ensure that the authenticated participant is the same as the participant whose data is
        # being requested
        logger.warning("user %s tried to access view model for %s", request.user.participant, pgr)
        raise PermissionDenied("Access denied.")
    view_model_json = get_view_model_json(pgr, experiment=pgr.group.experiment)
    return JsonResponse(dumps({'success': True, 'view_model_json': view_model_json}))

@participant_required
def mobile_participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    pgr = participant.get_participant_group_relationship(experiment)
    all_activities = Activity.objects.all()
    view_model_json = get_view_model_json(pgr, all_activities, experiment)
    return render(request, 'lighterprints/mobile/index.html', {
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'view_model_json': view_model_json,
        'all_activities': all_activities,
        })

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    pgr = ParticipantGroupRelationship.objects.select_related('participant__user', 'group').get(participant=participant,
            group__experiment=experiment)
    if pgr is None:
        raise Http404("You do not appear to be participating in this experiment.")
    all_activities = Activity.objects.all()
    view_model_json = get_view_model_json(pgr, all_activities, experiment)
#    if request.mobile:
        # FIXME: change this to look up templates in a mobile templates directory?
#        logger.warning("mobile request detected by %s, but we're not ready for mobile apps", participant)
        #return redirect('https://vcweb.asu.edu/devfoot')
    return render(request, 'lighterprints/participate.html', {
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'view_model_json': view_model_json,
        'all_activities': all_activities,
        })

def checkin(request):
    form = GeoCheckinForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        latitude = form.cleaned_data['latitude']
        longitude = form.cleaned_data['longitude']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group', 'participant__user'), pk=participant_group_id)
        logger.debug("%s checking at at (%s, %s)", participant_group_relationship, latitude, longitude)
        if request.user.participant == participant_group_relationship.participant:
# perform checkin logic here, query foursquare API for nearest "green" venu
            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
                    categoryId=','.join(get_foursquare_category_ids()))
            logger.debug("Found venues: %s", venues)
            return JsonResponse(dumps({'success':True}))
        else:
            logger.warning("authenticated user %s tried to checkin at (%s, %s) for %s", request.user, latitude, longitude, participant_group_relationship)
    return JsonResponse(dumps({'success':False, 'message': 'Invalid request'}))
