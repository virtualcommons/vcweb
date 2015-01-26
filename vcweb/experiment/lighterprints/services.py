from collections import defaultdict
from datetime import datetime, date, time, timedelta
from operator import itemgetter

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template import Context
from django.template.loader import select_template
from django.utils.timesince import timesince


from vcweb.core.models import (ParticipantRoundDataValue, ChatMessage, Like, Comment)
from .models import (Activity, is_scheduled_activity_experiment, get_activity_availability_cache, has_leaderboard,
                     get_activity_performed_parameter, ActivityAvailability, is_linear_public_good_experiment,
                     get_activity_points_cache, get_footprint_level, get_group_threshold, get_experiment_completed_dv,
                     get_footprint_level_dv, get_treatment_type, is_community_treatment, is_high_school_treatment,)

import itertools
import locale
import logging
import markdown
import re

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


def _activity_status_sort_key(activity_dict):
    s = activity_dict['status']
    if 'available' in s:
        return 1
    elif 'upcoming' in s:
        return 2
    elif 'expired' in s:
        return 3
    elif 'completed' in s:
        return 4
    else:
        return 5


class ActivityStatusList(object):

    """
    Partitions activities into available, completed, upcoming, and expired sets based on the participant group
    relationship parameter and the type of experiment being run (scheduled activity, level based, high school)
    """

    def __init__(self, participant_group_relationship, activities=None, round_configuration=None, group_level=1):
        self.activities = list(Activity.objects.all()) if activities is None else activities
        if round_configuration is None:
            round_configuration = participant_group_relationship.group.current_round
        self.round_configuration = round_configuration
        self.has_scheduled_activities = is_scheduled_activity_experiment(
            participant_group_relationship.group.experiment)
        # find all unlocked activities for the given participant
        self.all_unlocked_activities = Activity.objects.unlocked(self.round_configuration,
                                                                 scheduled=self.has_scheduled_activities,
                                                                 level=group_level)
        all_unlocked_activity_ids = self.all_unlocked_activities.values_list(
            'pk', flat=True)
        self.today = datetime.combine(date.today(), time())
        self.current_time = datetime.now().time()
        # first grab all the activities that have already been completed today
        completed_activity_dvs = participant_group_relationship.data_value_set.filter(
            parameter=get_activity_performed_parameter(),
            int_value__in=all_unlocked_activity_ids,
            date_created__gte=self.today)
        self.completed_activity_ids = completed_activity_dvs.values_list(
            'int_value', flat=True)
        # next, find all the activity availabilities for the unlocked activities and partition them into currently
        # available, upcoming, or expired
        activity_availabilities = ActivityAvailability.objects.select_related('activity').filter(
            activity__pk__in=all_unlocked_activity_ids)
        self.currently_available_activity_ids = activity_availabilities.filter(
            start_time__lte=self.current_time,
            end_time__gte=self.current_time).values_list('activity', flat=True)
        self.upcoming_activity_ids = activity_availabilities.filter(
            start_time__gte=self.current_time).values_list('activity', flat=True)
        self.initialize_activity_dict_list()

    def initialize_activity_dict_list(self):
        activity_availability_cache = get_activity_availability_cache()
        self.activity_dict_list = []
        for activity in self.activities:
            activity_dict = activity.to_dict()
            activity_status = self.get_activity_status(activity)
            activity_dict['status'] = activity_status
            activity_dict['availableNow'] = activity_status == 'available'
            activity_dict['availabilities'] = [aa.to_dict()
                                               for aa in activity_availability_cache[activity.pk]]
            self.activity_dict_list.append(activity_dict)
        self.activity_dict_list.sort(key=_activity_status_sort_key)

    def get_activity_status(self, activity):
        activity_status = 'locked'
        if activity in self.all_unlocked_activities:
            # check for 1. has activity already been completed 2. activity
            # time slot eligibility
            if activity.pk in self.completed_activity_ids:
                activity_status = 'completed'
            elif activity.pk in self.currently_available_activity_ids:
                activity_status = 'available'
            elif activity.pk in self.upcoming_activity_ids:
                activity_status = 'upcoming'
            else:
                activity_status = 'expired'
        return activity_status


class GroupScores(object):

    """ Data model encapsulating group scores across all treatments. Used by view models that are
    ParticipantGroupRelationship-specific, and by the nightly email service that aggregates group information and sends
    personalized email digests containing that day's group activity to each group. """

    def __init__(self, experiment, round_data=None, round_configuration=None, groups=None,
                 participant_group_relationship=None, experiment_configuration=None):
        self.experiment = experiment
        if round_data is None:
            round_data = experiment.current_round_data
        if round_configuration is None:
            round_configuration = round_data.round_configuration
        if groups is None:
            groups = list(experiment.groups)
        if experiment_configuration is None:
            experiment_configuration = experiment.experiment_configuration
        if participant_group_relationship is not None:
            # FIXME: used to construct a view model. distinction between view model and GroupScores is becoming
            # increasingly tenuous
            self.participant_group_relationship = participant_group_relationship
            self.group = participant_group_relationship.group
        self.experiment_configuration = experiment_configuration
        self.round_data = round_data
        self.round_configuration = round_configuration
        self.groups = groups
        self.exchange_rate = float(experiment_configuration.exchange_rate)
# FIXME: death by a thousand small inefficiencies, better to pull all ExperimentParameterValues instead of issuing
# multiple queries. look into updating API to handle this better for a given session
        self.is_linear_public_good_experiment = is_linear_public_good_experiment(experiment_configuration)
        self.has_leaderboard = has_leaderboard(experiment_configuration)
        self.number_of_groups = len(groups)
        # { group : {average_daily_points, total_daily_points} }
        self.group_rankings = None
        self.total_participant_points = 0
        # establish date range
        self.treatment_type = get_treatment_type(experiment_configuration=experiment_configuration).string_value
        self.initialize_scores(participant_group_relationship)

    # FIXME: refactor this logic strewn across models.py and services.py
    @property
    def is_level_based_experiment(self):
        return self.treatment_type == 'LEVEL_BASED'

    @property
    def has_scheduled_activities(self):
        return self.treatment_type != 'LEVEL_BASED'

    @property
    def is_high_school_treatment(self):
        return is_high_school_treatment(treatment_type=self.treatment_type)

    @property
    def is_community_treatment(self):
        return is_community_treatment(treatment_type=self.treatment_type)

    @property
    def group_clusters(self):
        return self.experiment.group_cluster_set

    def linear_public_good_configuration_check(self, activity_points_cache):
        if self.is_linear_public_good_experiment:
            all_activities_performed_qs = ParticipantRoundDataValue.objects.for_experiment(
                experiment=self.experiment,
                parameter=get_activity_performed_parameter())
            for dv in all_activities_performed_qs:
                activity_points = activity_points_cache[dv.int_value]
                self.scores_dict[dv.participant_group_relationship.group]['total_points'] += activity_points

    def community_treatment_initialization_check(self):
        if self.is_community_treatment:
            self.group_cluster_data = {}
            group_size = self.experiment_configuration.max_group_size
            for gc in self.group_clusters.all():
                total_daily_cluster_points = 0
                groups = list(gc.groups)
                number_of_groups = len(groups)
                for group in groups:
                    total_daily_cluster_points += self.scores_dict[group]['total_daily_points']
# cache the group cluster that this group belongs to
                    if group == self.group:
                        self.group_cluster = gc
                average_daily_cluster_points = total_daily_cluster_points / (number_of_groups * group_size)
                self.group_cluster_data[gc] = {
                    'total_daily_points': total_daily_cluster_points,
                    'average_daily_points': average_daily_cluster_points
                }
                for group in groups:
                    group_data_dict = self.scores_dict[group]
                    group_data_dict['total_daily_cluster_points'] = total_daily_cluster_points
                    group_data_dict['average_daily_cluster_points'] = average_daily_cluster_points

    def initialize_scores(self, participant_group_relationship):
        self.scores_dict = defaultdict(lambda: defaultdict(lambda: 0))
        activity_points_cache = get_activity_points_cache()
        activities_performed_qs = ParticipantRoundDataValue.objects.for_round(
            parameter=get_activity_performed_parameter(), round_data=self.round_data)
        for dv in activities_performed_qs:
            activity_points = activity_points_cache[dv.int_value]
            self.scores_dict[dv.participant_group_relationship.group]['total_daily_points'] += activity_points
            if participant_group_relationship and dv.participant_group_relationship == participant_group_relationship:
                self.total_participant_points += activity_points

        self.linear_public_good_configuration_check(activity_points_cache)
        for group in self.groups:
            group_data_dict = self.scores_dict[group]
            group_size = group.size
            group_data_dict['average_daily_points'] = group_data_dict['total_daily_points'] / group_size
            group_data_dict['total_average_points'] = group_data_dict['total_points'] / group_size
        self.community_treatment_initialization_check()

    def average_daily_points(self, group):
        return self.scores_dict[group]['average_daily_points']

    def daily_earnings(self, group):
        return self.average_daily_points(group) * self.exchange_rate

    def total_earnings(self, group):
        return self.total_average_points(group) * self.exchange_rate

    def total_earnings_currency(self, group):
        return locale.currency(self.total_earnings(group), grouping=True)

    def daily_earnings_currency(self, group):
        return locale.currency(self.daily_earnings(group), grouping=True)

    def total_average_points(self, group):
        return self.scores_dict[group]['total_average_points']

    def total_daily_points(self, group):
        return self.scores_dict[group]['total_daily_points']

    def get_group_level(self, group):
        if self.has_scheduled_activities:
            return 0
        else:
            return get_footprint_level(group, self.round_data)

    def get_points_goal(self, group):
        if self.has_scheduled_activities:
            # FIXME: hard coded limit for linear public good games, should be dependent on total number of scheduled
            # activities available per day instead?
            return 250 if self.is_linear_public_good_experiment else get_group_threshold(self.round_configuration)
        else:
            return get_points_to_next_level(self.get_group_level(group))

    def is_completed(self, group):
        if self.has_scheduled_activities:
            return self.average_daily_points(group) >= self.get_points_goal(group)
        else:
            return get_experiment_completed_dv(group, round_data=self.round_data).boolean_value

    def get_sorted_group_scores(self):
        return sorted(self.scores_dict.items(),
                      key=lambda x: x[1]['average_daily_points'],
                      reverse=True)

    def should_advance_level(self, group, level, max_level=3):
        logger.debug("checking if group %s at level %s should advance in level: %s",
                     group, level, self.scores_dict[group])
        if level <= max_level:
            return self.average_daily_points(group) >= get_points_to_next_level(level)
        return False

    def get_group_rank(self, group):
        return self.get_group_ranking_list().index(group) + 1

    def get_group_ranking_list(self):
        """
        Returns a sorted list of groups, ordered by their rank where the first item in the list is in first place,
        the second item in the list is in second place, and so on.
        """
        # cached because we invoke this often via get_group_rank
        if self.group_rankings is None:
            self.group_rankings = [g[0]
                                   for g in self.get_sorted_group_scores()]
        return self.group_rankings

    def get_group_cluster_data_list(self):
        return self.get_group_data_list(groups=self.group_cluster.groups)

    def get_group_data_list(self, groups=None):
        # FIXME: cache group_data if multiple invocations occur
        if groups is None:
            groups = self.groups
        group_data = []
        for group in groups:
            group_data.append(self.to_dict(group))
        group_data.sort(key=itemgetter('averagePoints'), reverse=True)
        return group_data

    def to_dict(self, group):
        return {
            'groupName': group.name,
            'groupLevel': self.get_group_level(group),
            'groupSize': group.size,
            'averagePoints': self.average_daily_points(group),
            'totalPoints': self.total_daily_points(group),
            'member': group == self.group
        }

    def generate_daily_update_messages(self):
        logger.debug("creating daily update email messages for all groups")
        return itertools.chain.from_iterable(self.update(group) for group in self.groups)

    def update(self, group):
        if self.is_level_based_experiment:
            # calculate total carbon savings and determine if the group should
            # advance to the next level
            return self.update_level_experiment(group)
        else:
            return self.update_scheduled_activity_experiment(group)

    def update_scheduled_activity_experiment(self, group):
        # FIXME: remove code duplication / redundancy between this and
        # create_level_experiment_email_messages
        round_data = self.round_data
        logger.debug("Calculating thresholds for scheduled activity experiment")
        threshold = self.get_points_goal(group)
        average_group_points = self.average_daily_points(group)
        logger.debug("threshold: %s vs average group points: %s", threshold, average_group_points)
        goal_reached = average_group_points >= threshold
        # they reached their goal, set their completion flag for this round
        get_experiment_completed_dv(group, round_data=round_data).update_boolean(goal_reached)
        yesterday = date.today() - timedelta(1)
        plaintext_template = select_template(['lighterprints/email/scheduled-activity/group-summary-email.txt'])
        experiment = group.experiment
        # experimenter_email = experiment.experimenter.email
        # FIXME: change this to the experimenter or add a dedicated settings
        # email from
        experimenter_email = settings.SERVER_EMAIL
        number_of_chat_messages = ChatMessage.objects.for_group(group, round_data=round_data).count()
        messages = []
        c = Context({
            'experiment': experiment,
            'experiment_completed': experiment.is_last_round,
            'number_of_groups': self.number_of_groups,
            'group_name': group.name,
            'group_rank': self.get_group_rank(group),
            'summary_date': yesterday,
            'threshold': threshold,
            'average_daily_points': average_group_points,
            'number_of_chat_messages': number_of_chat_messages,
            'linear_public_good': self.is_linear_public_good_experiment,
            'daily_earnings': self.daily_earnings_currency(group),
            'total_earnings': self.total_earnings_currency(group),
            'has_leaderboard': self.has_leaderboard
        })
        for pgr in group.participant_group_relationship_set.all():
            c['individual_points'] = get_individual_points(pgr, round_data)
            plaintext_content = plaintext_template.render(c)
            html_content = markdown.markdown(plaintext_content)
            subject = 'Lighter Footprints Summary for %s' % yesterday
            to_address = [experimenter_email, pgr.participant.email]
            msg = EmailMultiAlternatives(
                subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
        return messages

    def check_and_advance_level(self, group):
        footprint_level_grdv = get_footprint_level_dv(
            group, round_data=self.round_data)
        current_level = footprint_level_grdv.int_value
        promoted = False
        completed = False
        if self.should_advance_level(group, footprint_level_grdv.int_value):
            # group was promoted
            promoted = True
            next_level = min(current_level + 1, 3)
            footprint_level_grdv.update_int(next_level)
            if current_level == 3:
                completed = True
        group.copy_to_next_round(footprint_level_grdv)
        return {'promoted': promoted, 'completed': completed, 'level': footprint_level_grdv.int_value}

    def update_level_experiment(self, group):
        round_data = self.round_data
        experiment_completed_dv = get_experiment_completed_dv(
            group, round_data=round_data)
        already_completed = experiment_completed_dv.boolean_value
        if already_completed:
            # skip this group if it's already completed the experiment.
            return []
        level_status_dict = self.check_and_advance_level(group)
        group_summary_emails = self.create_level_based_group_summary_emails(
            group, **level_status_dict)
        # XXX: push into check_and_advance_level? would then have to thread experiment completed dv into method params
        # as well
        if level_status_dict['completed']:
            # store the completed flag for the group
            experiment_completed_dv.update_boolean(True)
        return group_summary_emails

    def create_level_based_group_summary_emails(self, group, level=1, promoted=False, completed=False):
        logger.debug(
            "creating level based group summary email for group %s", group)
        yesterday = date.today() - timedelta(1)
        experiment = group.experiment
        experimenter_email = experiment.experimenter.email
        plaintext_template = select_template(
            ['lighterprints/email/group-summary-email.txt'])
        number_of_chat_messages = ChatMessage.objects.for_group(
            group, round_data=self.round_data).count()
        summary_emails = []
        average_group_points = self.average_daily_points(group)
        points_to_next_level = get_points_to_next_level(level)
        c = Context(dict(experiment=experiment,
                         number_of_groups=self.number_of_groups,
                         group_name=group.name,
                         group_level=level,
                         group_rank=self.get_group_rank(group),
                         summary_date=yesterday,
                         has_leaderboard=self.has_leaderboard,
                         points_to_next_level=points_to_next_level,
                         average_daily_points=average_group_points,
                         number_of_chat_messages=number_of_chat_messages,
                         promoted=promoted,
                         completed=completed)
                    )
        for pgr in group.participant_group_relationship_set.all():
            c['individual_points'] = get_individual_points(pgr)
            plaintext_content = plaintext_template.render(c)
            html_content = markdown.markdown(plaintext_content)
            subject = 'Lighter Footprints Summary for %s' % yesterday
            to_address = [experimenter_email, pgr.participant.email]
            msg = EmailMultiAlternatives(
                subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            summary_emails.append(msg)
        return summary_emails

    def __str__(self):
        return str(self.scores_dict)


class GroupActivity(object):

    """ Models group activity anchored from the POV of a given ParticipantGroupRelationship """

    def __init__(self, participant_group_relationship, limit=None):
        self.participant_group_relationship = participant_group_relationship
        self.limit = limit
# maps parameter names to lists of the parameter data values
        self.all_activity = defaultdict(list)
        # FIXME: consider using InheritanceManager or manually selecting likes, comments, chatmessages, activities
        # performed to avoid n+1 selects when doing a to_dict
        group = participant_group_relationship.group
        data_values = ParticipantRoundDataValue.objects.for_group(group).with_parameter_names(
            names=('chat_message', 'comment', 'like', 'activity_performed'))
# assign data value ids generated by this participant, targeted by other
# participant's Likes or Comments
        like_target_ids = Like.objects.target_ids(participant_group_relationship)
        comment_target_ids = Comment.objects.target_ids(participant_group_relationship)
        if self.limit is not None:
            data_values = data_values[:self.limit]
        for prdv in data_values:
            parameter_name = prdv.parameter.name
            if parameter_name == 'chat_message':
                data = prdv.chatmessage.to_dict()
            elif parameter_name in ('comment', 'like'):
                data = getattr(prdv, parameter_name).to_dict()
            elif parameter_name == 'activity_performed':
                activity = prdv.cached_value
                data = activity.to_dict(attrs=('display_name', 'name', 'icon_url', 'savings', 'points'))
                pgr = prdv.participant_group_relationship
                data.update(
                    pk=prdv.pk,
                    date_created=abbreviated_timesince(prdv.date_created),
                    participant_number=pgr.participant_number,
                    participant_name=pgr.full_name,
                    participant_group_id=pgr.pk,
                )
            else:
                logger.warn("Invalid participant round data value %s", prdv)
                continue
            data.update(
                liked=prdv.pk in like_target_ids,
                commented=prdv.pk in comment_target_ids,
                parameter_name=parameter_name,
                date_created=abbreviated_timesince(prdv.date_created),
                dc=prdv.date_created,
            )
            self.all_activity[parameter_name].append(data)

    @property
    def all_activities(self):
        return sorted(itertools.chain.from_iterable(self.all_activity.values()), key=lambda x: x['dc'], reverse=True)

    @property
    def chat_messages(self):
        return self.all_activity['chat_message']

    @property
    def comments(self):
        return self.all_activity['comment']

    @property
    def likes(self):
        return self.all_activity['like']

    @property
    def performed_activities(self):
        return self.all_activity['activity_performed']


@transaction.atomic
def do_activity(activity, participant_group_relationship):
    round_data = participant_group_relationship.current_round_data
    if Activity.objects.is_activity_available(activity, participant_group_relationship, round_data):
        logger.debug("pgr %d performing available activity %s",
                     participant_group_relationship.pk, activity)
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                                                        participant_group_relationship=participant_group_relationship,
                                                        round_data=round_data,
                                                        int_value=activity.pk,
                                                        submitted=True)


def get_time_remaining():
    """ returns the hours and minutes till midnight """
    now = datetime.now()
    midnight = datetime.combine(date.today() + timedelta(1), time())
    time_remaining = midnight - now
    seconds_left = time_remaining.seconds
    total_minutes_left = seconds_left / 60
    hours_left = total_minutes_left / 60
    # pad minutes to have a leading 0 for single digits
    minutes = str(total_minutes_left % 60).zfill(2)
    return hours_left, minutes


def get_group_activity(participant_group_relationship, limit=None):
    group = participant_group_relationship.group
    all_activity = []
    chat_messages = []
    # FIXME: consider using InheritanceManager or manually selecting likes, comments, chatmessages, activities performed
    # to avoid n+1 selects when doing a to_dict
    data_values = ParticipantRoundDataValue.objects.for_group(group, parameter__name__in=('chat_message',
                                                                                          'comment',
                                                                                          'like',
                                                                                          'activity_performed'))
    like_target_ids = Like.objects.target_ids(participant_group_relationship)
    comment_target_ids = Comment.objects.target_ids(
        participant_group_relationship)
    if limit is not None:
        data_values = data_values[:limit]
    for prdv in data_values:
        parameter_name = prdv.parameter.name
        if parameter_name == 'chat_message':
            data = prdv.chatmessage.to_dict()
            chat_messages.append(data)
        elif parameter_name in ('comment', 'like'):
            # filters out comments not directed at the given participant_group_relationship (parameter to this method)
            # FIXME: extra query per comment
            if prdv.target_data_value.participant_group_relationship != participant_group_relationship:
                continue
            data = getattr(prdv, parameter_name).to_dict()
        elif parameter_name == 'activity_performed':
            activity = prdv.cached_value
            data = activity.to_dict(
                attrs=('display_name', 'name', 'icon_url', 'savings', 'points'))
            pgr = prdv.participant_group_relationship
            data.update(
                pk=prdv.pk,
                date_created=abbreviated_timesince(prdv.date_created),
                participant_number=pgr.participant_number,
                participant_name=pgr.full_name,
                participant_group_id=pgr.pk,
            )
        else:
            logger.warn("Invalid participant round data value %s", prdv)
            continue
        data.update(
            liked=prdv.pk in like_target_ids,
            commented=prdv.pk in comment_target_ids,
            parameter_name=parameter_name,
            date_created=abbreviated_timesince(prdv.date_created),
        )
        all_activity.append(data)
    return all_activity, chat_messages


def daily_update(experiment, debug=False, round_data=None, **kwargs):
    """
    Triggered by round_ended_handler in experiment/lighterprints/signals.py, uses experiment.current_round_data if not
    explicitly set which assumes that the experiment has *not* advanced to the next round yet.
    """
    all_messages = None
    with transaction.atomic():
        round_data = experiment.current_round_data if round_data is None else round_data
        logger.debug("sending summary emails to %s for round %s", experiment, round_data)
        group_scores = GroupScores(experiment, round_data, list(experiment.groups))
        all_messages = list(group_scores.generate_daily_update_messages())
    if not debug and all_messages:
        logger.debug("sending %s generated emails for lighter footprints", len(all_messages))
        mail.get_connection().send_messages(all_messages)


def abbreviated_timesince(dt):
    s = timesince(dt)
    s = re.sub(r'\sdays?', 'd', s)
    s = re.sub(r'\sminutes?', 'm', s)
    s = re.sub(r'\shours?', 'h', s)
    s = re.sub(r'\sweeks?', 'w', s)
    s = re.sub(r'\smonths?', 'mo', s)
    return s.replace(',', '')


def get_points_to_next_level(current_level):
    """ returns the number of average points needed to advance to the next level """
    if current_level == 1:
        return 50
    elif current_level == 2:
        return 125
    elif current_level == 3:
        return 225


def get_individual_points(participant_group_relationship, round_data=None, end_date=None):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
    prdvs = ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
                                                              round_data=round_data,
                                                              parameter=get_activity_performed_parameter())
    return Activity.objects.total(pks=prdvs.values_list('int_value', flat=True))
