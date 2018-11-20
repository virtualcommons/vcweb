import itertools
import locale
import logging
import re
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from operator import itemgetter

import markdown
from django.conf import settings
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import select_template
from django.utils.timesince import timesince

from vcweb.core.models import (ParticipantRoundDataValue, ChatMessage, Like, Comment)
from .models import (Activity, is_scheduled_activity_experiment, get_activity_availability_cache, has_leaderboard,
                     get_activity_performed_parameter, ActivityAvailability, is_linear_public_good_experiment,
                     get_activity_points_cache, get_footprint_level, get_group_threshold, get_experiment_completed_dv,
                     get_footprint_level_dv, get_treatment_type, is_community_treatment, is_high_school_treatment,
                     is_level_based_experiment, )

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

    def __init__(self, participant_group_relationship, activities=None, group_scores=None, group_level=1):
        self.activities = list(Activity.objects.all()) if activities is None else activities
        if group_scores is None:
            raise ValueError("group scores required")
        self.round_data = group_scores.round_data
        self.round_configuration = group_scores.round_configuration
        self.has_scheduled_activities = group_scores.has_scheduled_activities
        self.current_time = datetime.now().time()
        # find all unlocked activities for the given participant
        self.all_unlocked_activity_ids = Activity.objects.unlocked(
            self.round_configuration,
            scheduled=self.has_scheduled_activities,
            level=group_level).values_list('pk', flat=True)
        # first grab all the activities that have already been completed today
        completed_activity_dvs = participant_group_relationship.data_value_set.filter(
            parameter=get_activity_performed_parameter(),
            int_value__in=self.all_unlocked_activity_ids,
            round_data=self.round_data)
        self.completed_activity_ids = completed_activity_dvs.values_list('int_value', flat=True)
        # next, find all the activity availabilities for the unlocked activities and partition them into currently
        # available, upcoming, or expired
        activity_availabilities = ActivityAvailability.objects.select_related('activity').filter(
            activity__pk__in=self.all_unlocked_activity_ids)
        self.currently_available_activity_ids = activity_availabilities.filter(
            start_time__lte=self.current_time,
            end_time__gte=self.current_time).values_list('activity', flat=True)
        self.upcoming_activity_ids = activity_availabilities.filter(
            start_time__gte=self.current_time).values_list('activity', flat=True)
        self.initialize_activity_dict_list()

    def initialize_activity_dict_list(self):
        activity_availability_cache = get_activity_availability_cache()
        adl = []
        for activity in self.activities:
            activity_dict = activity.to_dict()
            activity_status = self.get_activity_status(activity.pk)
            activity_dict['status'] = activity_status
            activity_dict['availableNow'] = activity_status == 'available'
            activity_dict['availabilities'] = activity_availability_cache[activity.pk]
            adl.append(activity_dict)
        adl.sort(key=_activity_status_sort_key)
        self.activity_dict_list = adl

    def get_activity_status(self, activity_id):
        activity_status = 'locked'
        if activity_id in self.all_unlocked_activity_ids:
            # check for 1. has activity already been completed 2. activity
            # time slot eligibility
            if activity_id in self.completed_activity_ids:
                activity_status = 'completed'
            elif activity_id in self.currently_available_activity_ids:
                activity_status = 'available'
            elif activity_id in self.upcoming_activity_ids:
                activity_status = 'upcoming'
            else:
                activity_status = 'expired'
        return activity_status


class EmailGenerator(object):

    email_template = 'lighterprints/email/group-summary-email.txt'

    def __init__(self, group_scores):
        self.yesterday = date.today() - timedelta(1)
        self.experimenter_email = settings.DEFAULT_FROM_EMAIL
        self.experiment = group_scores.experiment
        self.experiment_configuration = group_scores.experiment_configuration
        self.round_data = group_scores.round_data
        self.treatment_type = group_scores.treatment_type
        self.has_leaderboard = group_scores.has_leaderboard
        self.group_scores = group_scores

    def __getattr__(self, attr):
        return getattr(self.group_scores, attr, None)

    def should_generate_emails(self, group):
        return True

    def get_context(self, group):
        experiment = self.experiment
        number_of_chat_messages = ChatMessage.objects.for_group(group, round_data=self.round_data).count()
        return {
            'experiment': experiment,
            'experiment_completed': experiment.is_last_round,
            'payment_information': self.experiment_configuration.payment_information,
            'number_of_groups': self.number_of_groups,
            'group_name': group.name,
            'summary_date': self.yesterday,
            'number_of_chat_messages': number_of_chat_messages,
            'treatment_type': self.treatment_type,
            'linear_public_good': self.is_linear_public_good_experiment,
            'group_rank': self.get_group_rank(group),
            'daily_earnings': self.daily_earnings_currency(group),
            'total_earnings': self.total_earnings_currency(group),
            'has_leaderboard': self.has_leaderboard
        }

    def generate(self, group):
        if not self.should_generate_emails(group):
            logger.debug("no need to generate emails for group %s", group)
            return []
        plaintext_template = select_template([self.email_template])
        # experimenter_email = experiment.experimenter.email
        round_data = self.round_data
        experimenter_email = self.experimenter_email
        context = self.get_context(group)
        messages = []
        for pgr in group.participant_group_relationship_set.all():
            context['individual_points'] = get_individual_points(pgr, round_data)
            plaintext_content = plaintext_template.render(context)
            html_content = markdown.markdown(plaintext_content)
            subject = 'Lighter Footprints Summary for %s' % self.yesterday.strftime('%b. %d %Y')
            to_address = [experimenter_email, pgr.participant.email]
            msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
        return messages


class LevelBasedEmailGenerator(EmailGenerator):

    def should_generate_emails(self, group):
        self.experiment_completed_dv = get_experiment_completed_dv(group, round_data=self.round_data)
        return not self.experiment_completed_dv.boolean_value

    def get_context(self, group):
        c = super(LevelBasedEmailGenerator, self).get_context(group)
        footprint_level_grdv = get_footprint_level_dv(group, round_data=self.round_data)
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
        current_level = footprint_level_grdv.int_value
        group.copy_to_next_round(footprint_level_grdv)
        if completed:
            self.experiment_completed_dv.update_boolean(True)
        c.update(dict(
            group_level=current_level,
            points_to_next_level=get_points_to_next_level(current_level),
            promoted=promoted,
            completed=completed))
        return c


class ScheduledActivityEmailGenerator(EmailGenerator):

    email_template = 'lighterprints/email/scheduled-activity/group-summary-email.txt'

    def get_context(self, group):
        context = super(ScheduledActivityEmailGenerator, self).get_context(group)
        # these aren't used for linear public good experiments introduced in Spring 2013
        threshold = self.get_points_goal(group)
        average_group_points = self.average_daily_points(group)
        goal_reached = average_group_points >= threshold
        context.update(dict(
            experiment_completed=self.experiment.is_last_round,
            average_daily_points=average_group_points,
            threshold=threshold,
            goal_reached=goal_reached,
        ))
        return context


class CommunityEmailGenerator(EmailGenerator):

    email_template = 'lighterprints/email/community/group-summary-email.txt'

    def get_context(self, group):
        context = super(CommunityEmailGenerator, self).get_context(group)
        # these aren't used for linear public good experiments introduced in Spring 2013
        context.update(dict(
            experiment_completed=self.experiment.is_last_round,
            average_daily_points=self.average_daily_points(group),
            average_daily_cluster_points=self.average_daily_cluster_points(group=group),
            group_rank=self.get_group_cluster_rank(group),
        ))
        return context


class GroupScores(object):

    """ Data model encapsulating group scores across all treatments. Used by view models that are
    ParticipantGroupRelationship-specific, and by the nightly email service that aggregates group information and sends
    personalized email digests containing that day's group activity to each group. """

    email_generators = {
        'COMMUNITY': CommunityEmailGenerator,
        'SCHEDULED_ACTIVITY': ScheduledActivityEmailGenerator,
        'LEVEL_BASED': LevelBasedEmailGenerator
    }

    def __init__(self, experiment, round_data=None, round_configuration=None, groups=None,
                 experiment_configuration=None):
        self.experiment = experiment
        if round_data is None:
            round_data = experiment.current_round_data
        if round_configuration is None:
            round_configuration = round_data.round_configuration
        if groups is None:
            groups = list(experiment.groups)
        if experiment_configuration is None:
            experiment_configuration = experiment.experiment_configuration
        self.experiment_configuration = experiment_configuration
        self.round_data = round_data
        self.round_configuration = round_configuration
        self.groups = groups
        self.group_dict = dict([(g.pk, g) for g in groups])
        self.exchange_rate = float(experiment_configuration.exchange_rate)
# FIXME: death by a thousand small inefficiencies, better to pull all ExperimentParameterValues instead of issuing
# multiple queries. look into updating API to handle this better for a given session
        self.is_linear_public_good_experiment = is_linear_public_good_experiment(experiment_configuration)
        self.has_leaderboard = has_leaderboard(experiment_configuration)
        self.number_of_groups = len(groups)
        # { group : {average_daily_points, total_daily_points} }
        self.group_rankings = None
        self.group_cluster_cache = {}
        self.group_cluster_rankings = {}
        self.total_participant_points = 0
        # establish date range
        self.treatment_type = get_treatment_type(experiment_configuration=experiment_configuration).string_value
        self.initialize_scores()

    def get_groups(self, group_id_list):
        gd = self.group_dict
        return [gd[pk] for pk in group_id_list]

    @property
    def is_level_based_experiment(self):
        return is_level_based_experiment(treatment_type=self.treatment_type)

    @property
    def has_scheduled_activities(self):
        return is_scheduled_activity_experiment(treatment_type=self.treatment_type)

    @property
    def is_high_school_treatment(self):
        return is_high_school_treatment(treatment_type=self.treatment_type)

    @property
    def is_community_treatment(self):
        return is_community_treatment(treatment_type=self.treatment_type)

    @property
    def group_clusters(self):
        return self.experiment.group_cluster_set

    def community_treatment_initialization_check(self):
        if self.is_community_treatment:
            self.group_cluster_data = {}
            group_size = self.experiment_configuration.max_group_size
            for gc in self.group_clusters.all():
                total_cluster_points = 0
                total_daily_cluster_points = 0
                group_ids = list(gc.group_ids)
                self.number_of_groups = len(group_ids)
                cluster_rankings = []
                for group_id in group_ids:
                    total_cluster_points += self.scores_dict[group_id]['total_points']
                    daily_group_points = self.scores_dict[group_id]['total_daily_points']
                    total_daily_cluster_points += daily_group_points
                    self.group_cluster_cache[group_id] = gc
                    cluster_rankings.append({'pk': group_id, 'points': daily_group_points})
                self.group_cluster_rankings[gc] = [x['pk'] for x in sorted(cluster_rankings,
                                                                           key=itemgetter('points'),
                                                                           reverse=True)]
                total_number_of_participants = self.number_of_groups * group_size
                average_daily_cluster_points = total_daily_cluster_points / total_number_of_participants
                total_average_points = total_cluster_points / total_number_of_participants
                self.group_cluster_data[gc] = {
                    'total_daily_points': total_daily_cluster_points,
                    'average_daily_points': average_daily_cluster_points,
                    'total_average_points': total_average_points,
                }

                for group_id in group_ids:
                    group_data_dict = self.scores_dict[group_id]
                    group_data_dict.update(
                        total_average_cluster_points=total_average_points,
                        total_daily_cluster_points=total_daily_cluster_points,
                        average_daily_cluster_points=average_daily_cluster_points,
                    )

    def initialize_scores(self):
        self.scores_dict = defaultdict(lambda: defaultdict(lambda: 0))
        self.participant_dict = defaultdict(lambda: defaultdict(lambda: 0))
        activity_points_cache = get_activity_points_cache()
        if self.is_linear_public_good_experiment:
            # tally all green points earned across the entire experiment
            all_activities_performed_qs = ParticipantRoundDataValue.objects.for_experiment(
                experiment=self.experiment,
                parameter=get_activity_performed_parameter())
            for dv in all_activities_performed_qs:
                activity_points = activity_points_cache[dv.int_value]
                pgr = dv.participant_group_relationship
                self.scores_dict[pgr.group.pk]['total_points'] += activity_points
                self.participant_dict[pgr]['total_points'] += activity_points
                if dv.round_data == self.round_data:
                    self.scores_dict[pgr.group.pk]['total_daily_points'] += activity_points
                    self.participant_dict[pgr]['total_daily_points'] += activity_points
        else:
            # only tally daily points for the group and for each individual participant
            activities_performed_qs = ParticipantRoundDataValue.objects.for_round(
                parameter=get_activity_performed_parameter(), round_data=self.round_data)
            for dv in activities_performed_qs:
                activity_points = activity_points_cache[dv.int_value]
                pgr = dv.participant_group_relationship
                self.scores_dict[pgr.group.pk]['total_daily_points'] += activity_points
                self.participant_dict[pgr]['total_daily_points'] += activity_points

        # FIXME: assumes all groups are equally sized
        self.group_size = self.experiment_configuration.max_group_size
        for group in self.groups:
            group_data_dict = self.scores_dict[group.pk]
            group_data_dict['average_daily_points'] = group_data_dict['total_daily_points'] / self.group_size
            group_data_dict['total_average_points'] = group_data_dict['total_points'] / self.group_size
        self.community_treatment_initialization_check()

    def average_daily_cluster_points(self, group_cluster=None, group=None):
        if group_cluster is not None:
            return self.group_cluster_data[group_cluster]['average_daily_points']
        elif group is not None:
            return self.scores_dict[group.pk]['average_daily_cluster_points']
        raise ValueError("no group or group cluster specified")

    def total_daily_cluster_points(self, group_cluster=None, group=None):
        if group_cluster is not None:
            return self.group_cluster_data[group_cluster]['total_daily_points']
        elif group is not None:
            return self.scores_dict[group.pk]['total_daily_cluster_points']
        raise ValueError("no group or group cluster specified")

    def total_average_cluster_points(self, group_cluster=None, group=None):
        if group_cluster is not None:
            return self.group_cluster_data[group_cluster]['total_average_points']
        elif group is not None:
            return self.scores_dict[group.pk]['total_average_cluster_points']
        raise ValueError("no group or group cluster specified")

    def average_daily_points(self, group):
        """
        Returns the average group score for this group for the current round / day.
        """
        return self.scores_dict[group.pk]['average_daily_points']

    def daily_earnings(self, group):
        if self.is_community_treatment:
            average_points = self.average_daily_cluster_points(group=group)
        else:
            average_points = self.average_daily_points(group)
        return average_points * self.exchange_rate

    def total_earnings(self, group):
        if self.is_community_treatment:
            total_points = self.total_average_cluster_points(group=group)
        else:
            total_points = self.total_average_points(group)
        return total_points * self.exchange_rate

    def total_earnings_currency(self, group):
        return locale.currency(self.total_earnings(group), grouping=True)

    def daily_earnings_currency(self, group):
        return locale.currency(self.daily_earnings(group), grouping=True)

    def total_average_points(self, group):
        """
        Returns the average group score for this group over the entire experiment, not just the current round / day.
        """
        return self.scores_dict[group.pk]['total_average_points']

    def total_daily_points(self, group):
        return self.scores_dict[group.pk]['total_daily_points']

    def get_group_level(self, group):
        if self.has_scheduled_activities:
            return 0
        else:
            return get_footprint_level(group, self.round_data)

    def get_points_goal(self, group):
        if self.has_scheduled_activities:
            # FIXME: hard coded limit for linear public good games, should be dependent on total number of scheduled
            # activities available per day instead?
            return get_group_threshold(self.experiment_configuration)
        else:
            return get_points_to_next_level(self.get_group_level(group))

    def is_completed(self, group):
        if self.has_scheduled_activities:
            return self.average_daily_points(group) >= self.get_points_goal(group)
        else:
            return get_experiment_completed_dv(group, round_data=self.round_data).boolean_value

    def should_advance_level(self, group, level, max_level=3):
        logger.debug("checking if group %s at level %s should advance in level: %s",
                     group, level, self.scores_dict[group.pk])
        if level <= max_level:
            return self.average_daily_points(group) >= get_points_to_next_level(level)
        return False

    def get_group_cluster_rank(self, group):
        gc = self.group_cluster_cache[group.pk]
        return self.group_cluster_rankings[gc].index(group.pk) + 1

    def get_group_rank(self, group):
        return self.get_group_ranking_list().index(group) + 1

    def get_group_ranking_list(self):
        """
        Returns a sorted list of groups, ordered by their rank where the first item in the list is in first place,
        the second item in the list is in second place, and so on.
        """
        # cached because we invoke this often via get_group_rank
        if self.group_rankings is None:
            sorted_group_scores = sorted(list(self.scores_dict.items()),
                                         key=lambda x: x[1]['average_daily_points'],
                                         reverse=True)
            group_dict = self.group_dict
            # g[0] is a group pk instead of the actual group, retrieve the actual group via self.group_dict
            self.group_rankings = [group_dict[g[0]] for g in sorted_group_scores]
        return self.group_rankings

    def get_group_cluster_data_list(self, group_cluster):
        groups = self.get_groups(group_cluster.groups)
        gdl = self.get_group_data_list(groups=groups)
        average_cluster_points = self.average_daily_cluster_points(group_cluster)
        total_cluster_points = self.total_daily_cluster_points(group_cluster)
        for d in gdl:
            d.update(averageClusterPoints=average_cluster_points,
                     totalClusterPoints=total_cluster_points)
        return gdl

    def get_group_data_list(self, groups=None):
        # FIXME: cache group_data if multiple invocations occur
        if groups is None:
            groups = self.groups
        group_data = [self.to_dict(g) for g in groups]
        group_data.sort(key=itemgetter('averagePoints'), reverse=True)
        return group_data

    def to_dict(self, group):
        return {
            'groupName': group.name,
            'groupLevel': self.get_group_level(group),
            'groupSize': self.group_size,
            'averagePoints': self.average_daily_points(group),
            'totalPoints': self.total_daily_points(group),
            'pk': group.pk,
        }

    @property
    def email_generator(self):
        return GroupScores.email_generators[self.treatment_type](self)

    def generate_daily_update_messages(self):
        email_generator = self.email_generator
        return itertools.chain.from_iterable(email_generator.generate(group) for group in self.groups)

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
                data = activity.to_dict()
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
                date_created_sort_key=prdv.date_created,
            )
            self.all_activity[parameter_name].append(data)

    @property
    def all_activities(self):
        return sorted(itertools.chain.from_iterable(list(self.all_activity.values())),
                      key=itemgetter('date_created_sort_key'), reverse=True)

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
    return None


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


def daily_update(experiment, debug=False, round_data=None, **kwargs):
    """
    Triggered by round_ended_handler in experiment/lighterprints/signals.py, uses experiment.current_round_data if not
    explicitly set which assumes that the experiment has *not* advanced to the next round yet.
    """
    all_messages = None
    with transaction.atomic():
        round_data = experiment.current_round_data if round_data is None else round_data
        logger.debug("sending summary emails to %s for round %s", experiment, round_data)
        group_scores = GroupScores(experiment, round_data=round_data, groups=list(experiment.groups))
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
