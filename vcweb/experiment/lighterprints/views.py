from datetime import datetime
import logging

from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
import unicodecsv

from vcweb.core.decorators import group_required, ownership_required
from vcweb.core.forms import (
    ChatForm, CommentForm, LikeForm, GeoCheckinForm, LoginForm)
from vcweb.core.http import JsonResponse
from vcweb.core.models import (ChatMessage, Comment, Experiment, ParticipantGroupRelationship,
                               ParticipantRoundDataValue, Like, PermissionGroup)
from vcweb.core.views import (dumps, get_active_experiment, set_authentication_token, mimetypes)
from .forms import ActivityForm
from .models import (Activity, get_lighterprints_experiment_metadata, is_linear_public_good_game,
                     is_high_school_treatment, get_treatment_type, get_activity_performed_parameter, )
from .services import (ActivityStatusList, GroupScores, do_activity, get_time_remaining, GroupActivity)


logger = logging.getLogger(__name__)


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def perform_activity(request):
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        logger.debug("%s request to perform activity %s", participant_group_id, activity_id)
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related(
                'participant__user', 'group__experiment'),
            pk=participant_group_id)
        #        latitude = form.cleaned_data['latitude']
        #        longitude = form.cleaned_data['longitude']
        if participant_group_relationship.participant == request.user.participant:
            activity = get_object_or_404(Activity, pk=activity_id)
            performed_activity = do_activity(activity=activity,
                                             participant_group_relationship=participant_group_relationship)
            # perform checkin logic here, query foursquare API for nearest "green" venu
            #            logger.debug("searching venues at %s,%s", latitude, longitude)
            #            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
            #                    categoryId=','.join(get_foursquare_category_ids()))
            #            logger.debug("Found venues: %s", venues)
            if performed_activity is not None:
                participant_group_relationship.set_first_visit()
                return JsonResponse({
                    'success': True,
                    'viewModel': get_view_model_dict(participant_group_relationship)
                })
            else:
                message = "Activity was not available at this time"
        else:
            message = "Unauthorized access: %s" % participant_group_relationship
            logger.warning("authenticated user %s tried to perform activity %s as %s", request.user, activity_id,
                           participant_group_relationship)
    logger.warning(message)
    return JsonResponse({'success': False, 'response': message})


@login_required
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user'),
                                pk=participant_group_id)
        if pgr.participant != request.user.participant:
            logger.warning(
                "authenticated user %s tried to post message %s as %s", request.user, message, pgr)
            return JsonResponse({'success': False, 'message': "Invalid request"})
        chat_message = ChatMessage.objects.create(
            value=message, participant_group_relationship=pgr)
        logger.debug("%s: %s", pgr.participant, chat_message)
        # FIXME: can optimize by only retrieving the latest group activity since the last checkin time
        group_activity = GroupActivity(pgr)
        return JsonResponse({'success': True, 'viewModel': {'groupActivity': group_activity.all_activities}})
    return JsonResponse({'success': False, 'message': "Invalid chat message post"})


@login_required
def like(request):
    form = LikeForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related(
                'participant__user', 'group__experiment'),
            pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to like target_id %s as %s", request.user, target_id,
                           participant_group_relationship)
            return JsonResponse({'success': False, 'message': "Invalid request"})
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        # FIXME: either needs a uniqueness constraint to ensure that duplicates don't get created or add guards when we
        # retrieve them to only send back the latest one (feels hacky).  See
        # https://bitbucket.org/virtualcommons/vcweb/issue/59/get_or_create-issues-for-likes
        round_data = participant_group_relationship.current_round_data
        Like.objects.create(round_data=round_data, participant_group_relationship=participant_group_relationship,
                            target_data_value=target)
        logger.debug(
            "Participant %s liked %s", participant_group_relationship, target)
        return JsonResponse({'success': True, 'viewModel': get_view_model_dict(participant_group_relationship)})
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse({'success': False, 'message': 'Invalid like post'})


@login_required
def post_comment(request):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related(
                'participant__user', 'group__experiment'),
            pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post comment %s on target %s as %s", request.user, message,
                           target_id, participant_group_relationship)
            return JsonResponse({'success': False, 'message': "Invalid request"})
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        Comment.objects.create(
            string_value=message,
            round_data=participant_group_relationship.current_round_data,
            participant_group_relationship=participant_group_relationship,
            target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s",
                     participant_group_relationship.participant, message, target)
        return JsonResponse({'success': True, 'viewModel': get_view_model_dict(participant_group_relationship)})
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse({'success': False, 'message': 'Invalid post comment'})


class LighterprintsViewModel(object):

    def __init__(self, participant_group_relationship, experiment=None, round_data=None):
        self.participant_group_relationship = participant_group_relationship
        self.group = participant_group_relationship.group
        self.experiment = self.group.experiment if experiment is None else experiment
        self.round_data = self.experiment.current_round_data if round_data is None else round_data


class HighSchoolViewModel(object):

    def __init__(self, participant_group_relationship, experiment=None, round_configuration=None, round_data=None):
        self.participant_group_relationship = participant_group_relationship
        self.group = participant_group_relationship.group
        self.experiment = self.group.experiment if experiment is None else experiment
        self.round_data = self.experiment.current_round_data if round_data is None else round_data
        self.round_configuration = self.experiment.current_round if round_configuration is None else round_configuration
        self.treatment_type = get_treatment_type(
            self.round_configuration).string_value
        self.experiment_configuration = self.experiment.experiment_configuration
        self.group_scores = GroupScores(experiment, round_data, participant_group_relationship)
        self.activities = []

    @property
    def activities(self):
        if not self.activities:
            self.activities = []
            completed_activity_pks = self.participant_group_relationship.data_value_set.filter(
                parameter=get_activity_performed_parameter(),
                round_data=self.round_data).values_list('int_value', flat=True)
            scheduled_activity_pks = Activity.objects.scheduled(
                self.round_configuration).values_list('pk', flat=True)
            for activity in Activity.objects.all():
                activity_dict = activity.to_dict()
                status = 'locked'
                if activity.pk in completed_activity_pks:
                    status = 'completed'
                elif activity.pk in scheduled_activity_pks:
                    status = 'available'
                activity_dict['status'] = status
                activity_dict['availableNow'] = status == 'available'
                activity_dict['availabilities'] = []
                self.activities.append(activity_dict)
        return self.activities

    def to_json(self):
        (hours_left, minutes_left) = get_time_remaining()
        participant_group_relationship = self.participant_group_relationship
        own_group = participant_group_relationship.group
        group_scores = self.group_scores
        group_activity = GroupActivity(participant_group_relationship)
        return dumps({
            'activities': self.activities,
            'quizCompleted': participant_group_relationship.survey_completed,
            'hasLeaderboard': True,
            'participantGroupId': participant_group_relationship.pk,
            'groupData': group_scores.get_group_data_list(),
            'hoursLeft': hours_left,
            'minutesLeft': minutes_left,
            'firstVisit': participant_group_relationship.first_visit,
            'averagePoints': group_scores.average_daily_points(own_group),
            'pointsToNextLevel': group_scores.get_points_goal(own_group),
            'groupActivity': group_activity.all_activities,
            'groupName': own_group.name,
            'totalPoints': group_scores.total_participant_points,
            'surveyUrl': self.round_configuration.make_survey_url(pid=participant_group_relationship.pk),
        })

    @property
    def template_name(self):
        return 'lighterprints/highschool.html'


@group_required(PermissionGroup.experimenter)
@ownership_required(Experiment)
def download_payment_data(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename=payment-%s' % experiment.data_file_name()
    writer = unicodecsv.writer(response, encoding='utf-8')
    group_scores = GroupScores(experiment)
    writer.writerow(['Group', 'Participant', 'Username', 'Total Earnings'])
    for pgr in experiment.participant_group_relationships:
        participant = pgr.participant
        group = pgr.group
        writer.writerow(
            [group, participant.email, participant.username, group_scores.total_earnings(group)])
    return response


def get_view_model_dict(participant_group_relationship, activities=None, experiment=None, round_configuration=None,
                        round_data=None):
    """
    FIXME: replace with view model class that stitches together ActivityStatusList and GroupScores appropriately and
    handles conditional switches between the different experiment types (scheduled activities, level based, high school)
    """
    own_group = participant_group_relationship.group
    if experiment is None:
        experiment = own_group.experiment
    if round_configuration is None:
        round_configuration = experiment.current_round
    experiment_configuration = round_configuration.experiment_configuration
    if is_high_school_treatment(experiment_configuration=experiment_configuration):
        return HighSchoolViewModel(participant_group_relationship, experiment, round_configuration).to_json()
    if activities is None:
        activities = Activity.objects.all()
    if round_data is None:
        round_data = experiment.current_round_data
    linear_public_good = is_linear_public_good_game(experiment_configuration)
    group_scores = GroupScores(experiment, round_data, participant_group_relationship=participant_group_relationship)
    total_participant_points = group_scores.total_participant_points
    group_data = group_scores.get_group_data_list()
    own_group_level = group_scores.get_group_level(own_group)
    activity_status_list = ActivityStatusList(participant_group_relationship, activities, round_configuration,
                                              group_level=own_group_level)
    group_activity = GroupActivity(participant_group_relationship)
    (hours_left, minutes_left) = get_time_remaining()
    return {
        'participantGroupId': participant_group_relationship.pk,
        'completed': group_scores.is_completed(own_group),
        'hasLeaderboard': group_scores.has_leaderboard,
        'groupData': group_data,
        'hoursLeft': hours_left,
        'minutesLeft': minutes_left,
        'firstVisit': participant_group_relationship.set_first_visit(),
        # FIXME: extract this from groupData instead..
        'groupLevel': own_group_level,
        'linearPublicGood': linear_public_good,
        'totalDailyEarnings': "{0:.2f}".format(group_scores.daily_earnings(own_group)),
        'totalEarnings': "{0:.2f}".format(group_scores.total_earnings(own_group)),
        'averagePoints': group_scores.average_daily_points(own_group),
        'pointsToNextLevel': group_scores.get_points_goal(own_group),
        'hasScheduledActivities': group_scores.has_scheduled_activities,
        'groupActivity': group_activity.all_activities,
        'groupName': own_group.name,
        'activities': activity_status_list.activity_dict_list,
        'totalPoints': total_participant_points,
    }


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def get_view_model(request, participant_group_id=None):
    if participant_group_id is None:
        # check in the request query parameters as well
        participant_group_id = request.GET.get('participant_group_id')
    # FIXME: replace with
    # ParticipantGroupRelationship.objects.fetch(pk=participant_group_id)
    pgr = get_object_or_404(
        ParticipantGroupRelationship.objects.select_related(
            'participant__user', 'group__experiment'),
        pk=participant_group_id)
    if pgr.participant != request.user.participant:
        # security check to ensure that the authenticated participant is the same as the participant whose data is
        # being requested
        logger.warning(
            "user %s tried to access view model for %s", request.user.participant, pgr)
        raise PermissionDenied("Access denied.")
    view_model = get_view_model_dict(pgr, experiment=pgr.group.experiment)
    return JsonResponse(dumps({'success': True, 'view_model_json': view_model}))


# FIXME: push this into core api/login if possible
def mobile_login(request):
    form = LoginForm(request.POST or None)
    try:
        if form.is_valid():
            user = form.user_cache
            logger.debug(
                "user was authenticated as %s, attempting to login", user)
            auth.login(request, user)
            set_authentication_token(user, request.session.session_key)
            return redirect('lighterprints:mobile_participate')
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return render(request, 'lighterprints/mobile/login.html')


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def mobile_participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_active_experiment(
        participant, experiment_metadata=get_lighterprints_experiment_metadata())
    pgr = experiment.get_participant_group_relationship(participant)
    all_activities = Activity.objects.all()
    view_model = get_view_model_dict(pgr, all_activities, experiment)
    return render(request, 'lighterprints/mobile/index.html', {
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'view_model_json': dumps(view_model),
        'all_activities': all_activities,
    })


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id,
                                   experiment_metadata=get_lighterprints_experiment_metadata())
    if experiment.is_active:
        round_configuration = experiment.current_round
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group'),
                                participant=participant, group__experiment=experiment)
        treatment_type = get_treatment_type(experiment).string_value
        if treatment_type == 'HIGH_SCHOOL':
            view_model = HighSchoolViewModel(pgr, experiment=experiment, round_configuration=round_configuration)
            return render(request, view_model.template_name, {
                'experiment': experiment,
                'participant_group_relationship': pgr,
                'view_model_json': view_model.to_json(),
            })

        all_activities = Activity.objects.all()
        view_model = get_view_model_dict(pgr, activities=all_activities, experiment=experiment,
                                         round_configuration=round_configuration)
        return render(request, 'lighterprints/participate.html', {
            'experiment': experiment,
            'participant_group_relationship': pgr,
            'has_leaderboard': treatment_type == 'LEADERBOARD',
            'view_model_json': dumps(view_model),
        })
    else:
        sd = experiment.start_date
        upcoming = sd > datetime.now().date() if sd is not None else False
        return render(request, 'lighterprints/inactive.html', {'experiment': experiment, 'upcoming': upcoming})


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def checkin(request):
    form = GeoCheckinForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        latitude = form.cleaned_data['latitude']
        longitude = form.cleaned_data['longitude']
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related('group', 'participant__user'), pk=participant_group_id)
        logger.debug("%s checking at at (%s, %s)",
                     participant_group_relationship, latitude, longitude)
        if request.user.participant == participant_group_relationship.participant:
            # perform checkin logic here, query foursquare API for nearest "green" venu
            #            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
            #                    categoryId=','.join(get_foursquare_category_ids()))
            #            logger.debug("Found venues: %s", venues)
            return JsonResponse(dumps({'success': True}))
        else:
            logger.warning("authenticated user %s tried to checkin at (%s, %s) for %s", request.user, latitude,
                           longitude, participant_group_relationship)
    return JsonResponse(dumps({'success': False, 'message': 'Invalid request'}))
