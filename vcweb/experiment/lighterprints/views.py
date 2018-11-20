import logging
from datetime import datetime

import unicodecsv
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from vcweb.core.decorators import group_required, ownership_required
from vcweb.core.forms import (ChatForm, CommentForm, LikeForm)
from vcweb.core.http import JsonResponse
from vcweb.core.models import (ChatMessage, Comment, Experiment, ParticipantGroupRelationship,
                               ParticipantRoundDataValue, Like, PermissionGroup)
from vcweb.core.views import (dumps, get_active_experiment, mimetypes)
from .forms import ActivityForm
from .models import (Activity, get_lighterprints_experiment_metadata, is_high_school_treatment, get_treatment_type,
                     get_activity_performed_parameter, is_community_treatment, is_level_based_experiment)
from .services import (ActivityStatusList, GroupScores, do_activity, get_time_remaining, GroupActivity)

logger = logging.getLogger(__name__)


class LighterprintsViewModel(object):
    template_name = 'lighterprints/participate.html'
    activity_limit = 60

    """ FIXME: more refactoring needed, continue to merge this with GroupScores """

    def __init__(self, participant_group_relationship, experiment=None,
                 round_configuration=None, round_data=None, activities=None):
        self.participant_group_relationship = participant_group_relationship
        self.group = participant_group_relationship.group
        self.experiment = self.group.experiment if experiment is None else experiment
        self.group_scores = GroupScores(self.experiment,
                                        round_data=round_data,
                                        round_configuration=round_configuration)
        self.group_activity = GroupActivity(participant_group_relationship, limit=self.activity_limit)
        self.total_participant_points = self.group_scores.total_participant_points
        self.activity_status_list = ActivityStatusList(participant_group_relationship,
                                                       activities=activities,
                                                       group_scores=self.group_scores,
                                                       group_level=self.own_group_level)

    @staticmethod
    def _get_model_class(treatment_type):
        if is_high_school_treatment(treatment_type=treatment_type):
            return HighSchoolViewModel
        elif is_community_treatment(treatment_type=treatment_type):
            return CommunityViewModel
        elif is_level_based_experiment(treatment_type=treatment_type):
            return LevelBasedViewModel
        else:
            return LighterprintsViewModel

    @staticmethod
    def create(participant_group_relationship, experiment=None, round_configuration=None,
               round_data=None, activities=None):
        if experiment is None:
            experiment = participant_group_relationship.experiment
        treatment_type = get_treatment_type(experiment).string_value
        klass = LighterprintsViewModel._get_model_class(treatment_type)
        return klass(participant_group_relationship, experiment, round_configuration, round_data, activities)

    def __getattr__(self, attr):
        return getattr(self.group_scores, attr, None)

    @property
    def own_group_level(self):
        return self.group_scores.get_group_level(self.group)

    @property
    def group_data(self):
        gdl = self.group_scores.get_group_data_list()
        for group_dict in gdl:
            group_dict['member'] = self.group.pk == group_dict['pk']
        return gdl

    def to_dict(self):
        (hours_left, minutes_left) = get_time_remaining()
        own_group = self.group
        participant_group_relationship = self.participant_group_relationship
        group_scores = self.group_scores
        own_group_level = group_scores.get_group_level(own_group)
        return {
            'participantGroupId': participant_group_relationship.pk,
            'completed': group_scores.is_completed(own_group),
            'hasLeaderboard': group_scores.has_leaderboard,
            'groupData': self.group_data,
            'hoursLeft': hours_left,
            'minutesLeft': minutes_left,
            'firstVisit': participant_group_relationship.first_visit,
            # FIXME: extract this from groupData, store & use group id as a key
            'groupLevel': own_group_level,
            'treatmentType': self.treatment_type,
            'linearPublicGood': group_scores.is_linear_public_good_experiment,
            'hasScheduledActivities': group_scores.has_scheduled_activities,
            'totalDailyEarnings': "{0:.2f}".format(group_scores.daily_earnings(own_group)),
            'totalEarnings': "{0:.2f}".format(group_scores.total_earnings(own_group)),
            'averagePoints': group_scores.average_daily_points(own_group),
            'pointsToNextLevel': group_scores.get_points_goal(own_group),
            'groupActivity': self.group_activity.all_activities,
            'groupName': own_group.name,
            'activities': self.activity_status_list.activity_dict_list,
            'totalPoints': self.total_participant_points,
        }

    def to_json(self):
        return dumps(self.to_dict())


class LevelBasedViewModel(LighterprintsViewModel):
    template_name = 'lighterprints/level-based.html'


class CommunityViewModel(LighterprintsViewModel):

    @property
    def group_cluster(self):
        return self.group.group_cluster

    @property
    def group_data(self):
        gdl = self.group_scores.get_group_cluster_data_list(self.group_cluster)
        for group_dict in gdl:
            group_dict['member'] = self.group.pk == group_dict['pk']
        return gdl

    def to_dict(self):
        d = super(CommunityViewModel, self).to_dict()
        d.update(averageClusterPoints=self.group_scores.average_daily_cluster_points(self.group_cluster),)
        return d


class HighSchoolViewModel(LighterprintsViewModel):
    template_name = 'lighterprints/highschool.html'

    @property
    def activities(self):
        if not self.activities:
            self.activities = []
            completed_activity_pks = self.participant_group_relationship.data_value_set.filter(
                parameter=get_activity_performed_parameter(),
                round_data=self.round_data).values_list('int_value', flat=True)
            scheduled_activity_pks = Activity.objects.scheduled(self.round_configuration).values_list('pk', flat=True)
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

    def to_dict(self):
        (hours_left, minutes_left) = get_time_remaining()
        participant_group_relationship = self.participant_group_relationship
        own_group = participant_group_relationship.group
        group_scores = self.group_scores
        return {
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
            'groupActivity': self.group_activity.all_activities,
            'groupName': own_group.name,
            'totalPoints': group_scores.total_participant_points,
            'surveyUrl': self.round_configuration.build_survey_url(pid=participant_group_relationship.pk),
        }


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def perform_activity(request):
    form = ActivityForm(request.POST or None)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        logger.debug("%s request to perform activity %s", participant_group_id, activity_id)
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'),
            pk=participant_group_id)
        if participant_group_relationship.participant == request.user.participant:
            activity = get_object_or_404(Activity, pk=activity_id)
            performed_activity = do_activity(activity=activity,
                                             participant_group_relationship=participant_group_relationship)
            experiment = participant_group_relationship.experiment
            if performed_activity is not None:
                participant_group_relationship.set_first_visit()
                return JsonResponse({
                    'success': True,
                    'viewModel': LighterprintsViewModel.create(participant_group_relationship, experiment).to_dict()
                })
            else:
                message = "Activity was not available at this time"
        else:
            message = "Unauthorized access logged for %s" % participant_group_relationship
            logger.warning("authenticated user %s tried to perform activity %s as %s", request.user, activity_id,
                           participant_group_relationship)
    return JsonResponse({'success': False, 'response': message})


@login_required
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user'),
                                pk=participant_group_id,
                                participant=request.user.participant,
                                )
        chat_message = ChatMessage.objects.create(string_value=message, participant_group_relationship=pgr)
        logger.debug("%s: %s", pgr.participant, chat_message)
        # FIXME: optimize, only retrieving the latest group activity since the last checkin time
        group_activity = GroupActivity(pgr, limit=LighterprintsViewModel.activity_limit)
        return JsonResponse({'success': True, 'viewModel': {'groupActivity': group_activity.all_activities}})
    return JsonResponse({'success': False, 'message': "Invalid chat message post"})


@login_required
def like(request):
    form = LikeForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        participant_group_relationship = get_object_or_404(
            ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'),
            pk=participant_group_id,
            participant=request.user.participant
        )
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        # FIXME: either needs a uniqueness constraint to ensure that duplicates don't get created or add guards when we
        # retrieve them to only send back the latest one (feels hacky).  See
        # https://bitbucket.org/virtualcommons/vcweb/issue/59/get_or_create-issues-for-likes
        round_data = participant_group_relationship.current_round_data
        Like.objects.create(round_data=round_data, participant_group_relationship=participant_group_relationship,
                            target_data_value=target)
        logger.debug("Participant %s liked %s", participant_group_relationship, target)
        return JsonResponse({'success': True})
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
            ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'),
            pk=participant_group_id,
            participant=request.user.participant,
        )
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        Comment.objects.create(
            string_value=message,
            round_data=participant_group_relationship.current_round_data,
            participant_group_relationship=participant_group_relationship,
            target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s",
                     participant_group_relationship.participant, message, target)
        return JsonResponse({'success': True,
                             'viewModel': LighterprintsViewModel.create(participant_group_relationship).to_dict()})
    else:
        logger.debug("invalid form: %s from request: %s", form.errors, request)
        return JsonResponse({'success': False, 'message': 'Invalid post comment'})


@group_required(PermissionGroup.experimenter)
@ownership_required(Experiment)
def download_payment_data(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response[
        'Content-Disposition'] = 'attachment; filename=payment-%s' % experiment.data_file_name()
    writer = unicodecsv.writer(response, encoding='utf-8')
    group_scores = GroupScores(experiment)
    writer.writerow(['Group', 'Participant', 'Username', 'Total Earnings'])
    for pgr in experiment.participant_group_relationships:
        participant = pgr.participant
        group = pgr.group
        writer.writerow([group, participant.email, participant.username, group_scores.total_earnings(group)])
    return response


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def get_view_model(request, participant_group_id=None):
    if participant_group_id is None:
        # check in the request query parameters as well
        participant_group_id = request.GET.get('participant_group_id')
    pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user',
                                                                                'group__experiment'),
                            pk=participant_group_id)
    if pgr.participant != request.user.participant:
        # check that authenticated participant is the same as the participant whose data is being requested
        logger.warning("user %s tried to access view model for %s", request.user.participant, pgr)
        raise PermissionDenied("You don't appear to have permission to access this experiment.")
    return JsonResponse({'success': True, 'viewModel': LighterprintsViewModel.create(pgr).to_dict()})


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    user = request.user
    participant = user.participant
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_configuration'), pk=experiment_id,
                                   experiment_metadata=get_lighterprints_experiment_metadata())
    if experiment.is_active:
        round_configuration = experiment.current_round
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group'),
                                participant=participant, group__experiment=experiment)
        view_model = LighterprintsViewModel.create(pgr, experiment, round_configuration=round_configuration)
        return render(request, view_model.template_name, {
            'experiment': experiment,
            'group_size': experiment.experiment_configuration.max_group_size,
            'participant_group_relationship': pgr,
            'has_leaderboard': view_model.has_leaderboard,
            'treatment_type': view_model.treatment_type,
            'linear_public_good': view_model.is_linear_public_good_experiment,
            'view_model_json': view_model.to_json(),
        })
    else:
        sd = experiment.start_date
        upcoming = sd > datetime.now().date() if sd is not None else False
        return render(request, 'lighterprints/inactive.html', {'experiment': experiment, 'upcoming': upcoming})


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def mobile_participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_active_experiment(participant, experiment_metadata=get_lighterprints_experiment_metadata())
    pgr = experiment.get_participant_group_relationship(participant)
    all_activities = Activity.objects.all()
    view_model = LighterprintsViewModel.create(pgr, experiment, activities=all_activities)
    return render(request, 'lighterprints/mobile/index.html', {
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'view_model_json': dumps(view_model),
        'all_activities': all_activities,
    })
