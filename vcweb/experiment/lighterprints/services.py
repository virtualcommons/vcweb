from collections import defaultdict
from datetime import datetime, date, time, timedelta
from operator import itemgetter

from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.dispatch import receiver
from django.template import Context
from django.template.loader import select_template
from django.utils.timesince import timesince

from vcweb.core import signals

from vcweb.core.models import (
    ParticipantRoundDataValue, ChatMessage, Experiment, Like, Comment)
from .models import (Activity, is_scheduled_activity_experiment, get_activity_availability_cache,
                     get_activity_performed_parameter, ActivityAvailability, _activity_status_sort_key,
                     is_linear_public_good_game, is_high_school_treatment, has_leaderboard, get_activity_points_cache,
                     get_footprint_level, get_group_threshold, get_points_to_next_level, get_experiment_completed_dv,
                     get_individual_points, get_footprint_level_dv, get_lighterprints_experiment_metadata)

import itertools
import locale
import logging
import markdown
import re

logger = logging.getLogger(__name__)


class ActivityStatusList(object):

    """
    Partitions activities into available, completed, upcoming, and expired sets based on the participant group
    relationship parameter and the type of experiment being run (scheduled activity, level based, high school)
    """

    def __init__(self, participant_group_relationship, activities=None, round_configuration=None, group_level=1):
        self.activities = list(Activity.objects.all()) if activities is None else activities
        activity_availability_cache = get_activity_availability_cache()
        if round_configuration is None:
            round_configuration = participant_group_relationship.group.current_round
        self.round_configuration = round_configuration
        self.has_scheduled_activities = is_scheduled_activity_experiment(
            self.round_configuration.experiment_configuration)
        # find all unlocked activities for the given participant
        self.all_unlocked_activities = Activity.objects.unlocked(self.round_configuration,
                                                                 scheduled=self.has_scheduled_activities,
                                                                 level=group_level)
        all_unlocked_activity_ids = self.all_unlocked_activities.values_list('pk', flat=True)
        self.today = datetime.combine(date.today(), time())
        self.current_time = datetime.now().time()
        # first grab all the activities that have already been completed today
        completed_activity_dvs = participant_group_relationship.data_value_set.filter(
            parameter=get_activity_performed_parameter(),
            int_value__in=all_unlocked_activity_ids,
            date_created__gte=self.today)
        self.completed_activity_ids = completed_activity_dvs.values_list('int_value', flat=True)
        # next, find all the activity availabilities for the unlocked activities and partition them into currently
        # available, upcoming, or expired
        activity_availabilities = ActivityAvailability.objects.select_related('activity').filter(
            activity__pk__in=all_unlocked_activity_ids)
        self.currently_available_activity_ids = activity_availabilities.filter(start_time__lte=self.current_time,
                                                                               end_time__gte=self.current_time).values_list('activity', flat=True)
        self.upcoming_activity_ids = activity_availabilities.filter(start_time__gte=self.current_time).values_list('activity', flat=True)
        self.activity_dict_list = [self.to_activity_dict(activity, activity_availability_cache) for activity in self.activities]
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

    def to_activity_dict(self, activity, activity_availability_cache=None):
        if activity_availability_cache is None:
            activity_availability_cache = get_activity_availability_cache()
        activity_dict = activity.to_dict()
        activity_status = self.get_activity_status(activity)
        activity_dict['status'] = activity_status
        activity_dict['availableNow'] = activity_status == 'available'
        activity_dict['availabilities'] = [aa.to_dict() for aa in activity_availability_cache[activity.pk]]
        return activity_dict


class GroupScores(object):

    def __init__(self, experiment, round_data=None, groups=None, participant_group_relationship=None, start_date=None,
                 end_date=None, experiment_configuration=None):
        self.experiment = experiment
        if round_data is None:
            round_data = experiment.current_round_data
        if groups is None:
            groups = list(experiment.groups)
        if experiment_configuration is None:
            experiment_configuration = experiment.experiment_configuration
        if start_date is None:
            start_date = date.today()
        self.round_data = round_data
        self.groups = groups
        self.experiment_configuration = experiment_configuration
        self.exchange_rate = float(experiment_configuration.exchange_rate)
        self.has_scheduled_activities = is_scheduled_activity_experiment(experiment_configuration)
        self.is_linear_public_good_game = is_linear_public_good_game(experiment_configuration)
        self.number_of_groups = len(groups)
        # { group : {average_daily_points, total_daily_points} }
        self.scores_dict = defaultdict(lambda: defaultdict(lambda: 0))
        self.group_rankings = None
        self.total_participant_points = 0
        # establish date range
        self.start_date = start_date
        self.end_date = start_date + timedelta(1) if end_date is None else end_date
        self.round_configuration = self.round_data.round_configuration
        self.is_high_school_treatment = is_high_school_treatment(self.round_configuration)
        self.has_leaderboard = has_leaderboard(self.round_configuration)
        self.initialize_scores(participant_group_relationship)

    def initialize_scores(self, participant_group_relationship):
        activity_points_cache = get_activity_points_cache()
        activities_performed_qs = ParticipantRoundDataValue.objects.for_round(
            parameter=get_activity_performed_parameter(), round_data=self.round_data,
            date_created__range=(self.start_date, self.end_date))
        for activity_performed_dv in activities_performed_qs:
            activity_points = activity_points_cache[activity_performed_dv.int_value]
            self.scores_dict[activity_performed_dv.participant_group_relationship.group]['total_daily_points'] += activity_points
            if participant_group_relationship and activity_performed_dv.participant_group_relationship == participant_group_relationship:
                self.total_participant_points += activity_points
        if self.is_linear_public_good_game:
            all_activities_performed_qs = ParticipantRoundDataValue.objects.for_experiment(experiment=self.experiment,
                                                                                           parameter=get_activity_performed_parameter())
            for activity_performed_dv in all_activities_performed_qs:
                activity_points = activity_points_cache[activity_performed_dv.int_value]
                self.scores_dict[activity_performed_dv.participant_group_relationship.group]['total_points'] += activity_points
        for group in self.groups:
            group_data_dict = self.scores_dict[group]
            group_size = group.size
            group_data_dict['average_daily_points'] = group_data_dict['total_daily_points'] / group_size
            group_data_dict['total_average_points'] = group_data_dict['total_points'] / group_size
            logger.debug("group data dictionary: %s", group_data_dict)

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
            return 250 if self.is_linear_public_good_game else get_group_threshold(self.round_configuration)
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
        logger.debug("checking if group %s at level %s should advance in level on %s (%s)",
                     group, level, self.start_date, self.scores_dict[group])
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
            self.group_rankings = [g[0] for g in self.get_sorted_group_scores()]
        return self.group_rankings

    def get_group_data_list(self):
        # FIXME: cache group_data if multiple invocations occur
        group_data = []
        for group in self.groups:
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
            'pointsToNextLevel': self.get_points_goal(group),
        }

    def create_all_email_messages(self):
        logger.debug("creating email messages for all groups")
        return itertools.chain.from_iterable(self.create_email_messages(group) for group in self.groups)

    def create_email_messages(self, group):
        if self.has_scheduled_activities:
            return self.create_scheduled_activity_experiment_emails(group)
        else:
            # calculate total carbon savings and determine if the group should
            # advance to the next level
            return self.create_level_experiment_emails(group)

    def create_scheduled_activity_experiment_emails(self, group):
        # FIXME: remove code duplication / redundancy between this and
        # create_level_experiment_email_messages
        round_data = self.round_data
        logger.debug(
            "Calculating thresholds for scheduled activity experiment")
        threshold = self.get_points_goal(group)
        average_group_points = self.average_daily_points(group)
        logger.debug(
            "threshold: %s vs average group points: %s", threshold, average_group_points)
        goal_reached = average_group_points >= threshold
        # they reached their goal, set their completion flag for this round
        get_experiment_completed_dv(
            group, round_data=round_data).update_boolean(goal_reached)
        yesterday = date.today() - timedelta(1)
        plaintext_template = select_template(
            ['lighterprints/email/scheduled-activity/group-summary-email.txt'])
        experiment = group.experiment
        #experimenter_email = experiment.experimenter.email
        experimenter_email = settings.SERVER_EMAIL
        number_of_chat_messages = ChatMessage.objects.filter(participant_group_relationship__group=group,
                                                             date_created__gte=yesterday).count()
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
            'linear_public_good': self.is_linear_public_good_game,
            'daily_earnings': self.daily_earnings_currency(group),
            'total_earnings': self.total_earnings_currency(group),
            'has_leaderboard': self.has_leaderboard
        })
        for pgr in group.participant_group_relationship_set.all():
            c['individual_points'] = get_individual_points(pgr)
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
        return {'promoted': promoted, 'completed': completed, 'level': footprint_level_grdv.int_value}

    def create_level_experiment_emails(self, group):
        round_data = self.round_data
        experiment_completed_dv = get_experiment_completed_dv(
            group, round_data=round_data)
        already_completed = experiment_completed_dv.boolean_value
        if already_completed:
            # skip this group if it's already completed the experiment.
            return []
        level_status_dict = self.check_and_advance_level(group)
        group_summary_emails = self.create_level_based_group_summary_emails(group, round_data=round_data,
                                                                            **level_status_dict)
        # XXX: push into check_and_advance_level? would then have to thread experiment completed dv into method params
        # as well
        if level_status_dict['completed']:
            # store the completed flag for the group
            experiment_completed_dv.update_boolean(True)
        return group_summary_emails

    def create_level_based_group_summary_emails(self, group, level=1, **kwargs):
        logger.debug(
            "creating level based group summary email for group %s", group)
        yesterday = date.today() - timedelta(1)
        plaintext_template = select_template(
            ['lighterprints/email/group-summary-email.txt'])
        experiment = group.experiment
        experimenter_email = experiment.experimenter.email
        number_of_chat_messages = ChatMessage.objects.filter(participant_group_relationship__group=group,
                                                             date_created__gte=yesterday).count()
        messages = []
        average_group_points = self.average_daily_points(group)
        points_to_next_level = get_points_to_next_level(level)
        c = Context(dict({'experiment': experiment,
                          'number_of_groups': self.number_of_groups,
                          'group_name': group.name,
                          'group_level': level,
                          'group_rank': self.get_group_rank(group),
                          'summary_date': yesterday,
                          'has_leaderboard': self.has_leaderboard,
                          'points_to_next_level': points_to_next_level,
                          'average_daily_points': average_group_points,
                          'number_of_chat_messages': number_of_chat_messages,
                          }, **kwargs))
        for pgr in group.participant_group_relationship_set.all():
            c['individual_points'] = get_individual_points(pgr)
            plaintext_content = plaintext_template.render(c)
            html_content = markdown.markdown(plaintext_content)
            subject = 'Lighter Footprints Summary for %s' % yesterday
            to_address = [experimenter_email, pgr.participant.email]
            msg = EmailMultiAlternatives(
                subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
        return messages

    def __str__(self):
        return str(self.scores_dict)


@receiver(signals.pre_system_daily_tick)
def send_summary_emails(sender, time=None, start_date=None, debug=False, round_configuration=None, **kwargs):
    """ FIXME: consider changing this into the round_ended handler and get rid of pre_system_daily_tick to get rid of
    potential concurrency issues where summary email generation bleeds into the system_daily_tick that advances the
    experiment to the next round.
    invoked after midnight, so start_date should be set to the previous day.
     """
    if start_date is None:
        start_date = date.today() - timedelta(1)
    all_messages = []
    with transaction.atomic():
        active_experiments = Experiment.objects.select_for_update().active(
            experiment_metadata=get_lighterprints_experiment_metadata())
        logger.debug(
            "sending summary emails to [%s] on %s", active_experiments, start_date)
        for experiment in active_experiments:
            # we use the current round data because this tick occurs *before* the system_daily_tick that advances each
            # experiment to the next round.
            round_data = experiment.current_round_data if round_configuration is None else experiment.get_round_data(
                round_configuration)
            group_scores = GroupScores(
                experiment, round_data, list(experiment.groups), start_date=start_date)
            all_messages.extend(group_scores.create_all_email_messages())
    if not debug and all_messages:
        logger.debug(
            "sending %s generated emails for lighter footprints", len(all_messages))
        mail.get_connection().send_messages(all_messages)


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
    # FIXME: consider using InheritanceManager or manually selecting likes, comments, chatmessages, activities performed to
    # avoid n+1 selects when doing a to_dict
    data_values = ParticipantRoundDataValue.objects.for_group(group)
    like_target_ids = Like.objects.target_ids(participant_group_relationship)
    comment_target_ids = Comment.objects.target_ids(participant_group_relationship)
    if limit is not None:
        data_values = data_values[:limit]
    for prdv in data_values:
        parameter_name = prdv.parameter.name
        if parameter_name == 'chat_message':
            data = prdv.chatmessage.to_dict()
            chat_messages.append(data)
        elif parameter_name == 'comment':
            # filters out comments not directed at the given participant_group_relationship (parameter to this method)
            # FIXME: this is expensive, does an extra query per comment
            if prdv.target_data_value.participant_group_relationship != participant_group_relationship:
                continue
            data = prdv.comment.to_dict()
        elif parameter_name == 'like':
            if prdv.target_data_value.participant_group_relationship != participant_group_relationship:
                continue
            data = prdv.like.to_dict()
        elif parameter_name == 'activity_performed':
            activity = prdv.cached_value
            data = activity.to_dict(attrs=('display_name', 'name', 'icon_url', 'savings', 'points'))
            data['pk'] = prdv.pk
            data['date_created'] = abbreviated_timesince(prdv.date_created)
            pgr = prdv.participant_group_relationship
            data['participant_number'] = pgr.participant_number
            data['participant_name'] = pgr.full_name
            data['participant_group_id'] = pgr.pk
        else:
            continue
        data['liked'] = prdv.pk in like_target_ids
        data['commented'] = prdv.pk in comment_target_ids
        data['parameter_name'] = parameter_name
        data['date_created'] = abbreviated_timesince(prdv.date_created)
        all_activity.append(data)
    return all_activity, chat_messages


def abbreviated_timesince(dt):
    s = timesince(dt)
    s = re.sub(r'\sdays?', 'd', s)
    s = re.sub(r'\sminutes?', 'm', s)
    s = re.sub(r'\shours?', 'h', s)
    s = re.sub(r'\sweeks?', 'w', s)
    s = re.sub(r'\smonths?', 'mo', s)
    return s.replace(',', '')
