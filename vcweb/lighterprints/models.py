from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import Sum
from django.dispatch import receiver
from django.template import Context
from django.template.loader import select_template
from django.utils.timesince import timesince
from model_utils.managers import PassThroughManager
from vcweb.core import signals, simplecache, enum
from vcweb.core.models import (Experiment, ExperimentMetadata, GroupRoundDataValue, RoundParameterValue, ParticipantRoundDataValue, Parameter, User, Comment, Like, ChatMessage)
from vcweb.core.services import fetch_foursquare_categories
from collections import defaultdict
from datetime import datetime, date, time, timedelta
from mptt.models import MPTTModel, TreeForeignKey, TreeManager
from operator import itemgetter
import re

import logging
logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = intern('lighterprints')


def get_activity_points_cache():
    cv = 'activity_points_cache'
    activity_points_cache = cache.get(cv)
    if activity_points_cache is None:
        activity_points_cache = dict([(a.pk, a.points) for a in Activity.objects.all()])
        #cache.set(cv, activity_points_cache, timedelta(days=1).total_seconds())
        cache.set(cv, activity_points_cache, 86400)
    return activity_points_cache


def is_scheduled_activity_experiment(experiment_configuration):
    return experiment_configuration.has_daily_rounds

class ActivityStatusList(object):

    def __init__(self, participant_group_relationship, activities=None, round_configuration=None, group_level=1):
        self.activities = list(Activity.objects.all()) if activities is None else activities
        self.round_configuration = participant_group_relationship.group.current_round if round_configuration is None else round_configuration
        self.has_scheduled_activities = is_scheduled_activity_experiment(self.round_configuration.experiment_configuration)
        activity_availability_cache = get_activity_availability_cache()
# find all unlocked activities for the given participant
        self.all_unlocked_activities = Activity.objects.unlocked(self.round_configuration, scheduled=self.has_scheduled_activities, level=group_level)
        all_unlocked_activity_ids = self.all_unlocked_activities.values_list('pk', flat=True)
        self.today = datetime.combine(date.today(), time())
        self.current_time = datetime.now().time()
        # first grab all the activities that have already been completed today
        completed_activity_dvs = participant_group_relationship.data_value_set.filter(parameter=get_activity_performed_parameter(),
                int_value__in=all_unlocked_activity_ids,
                date_created__gte=self.today)
        self.completed_activity_ids = completed_activity_dvs.values_list('int_value', flat=True)
        # next, find all the activity availabilities for the unlocked activities and partition them into currently
        # available, upcoming, or expired
        activity_availabilities = ActivityAvailability.objects.select_related('activity').filter(activity__pk__in=all_unlocked_activity_ids)
        self.currently_available_activity_ids = activity_availabilities.filter(start_time__lte=self.current_time, end_time__gte=self.current_time).values_list('activity', flat=True)
        self.upcoming_activity_ids = activity_availabilities.filter(start_time__gte=self.current_time).values_list('activity', flat=True)
        self.activity_dict_list = []
        for activity in self.activities:
            activity_dict = activity.to_dict()
            activity_status = 'locked'
            if activity in self.all_unlocked_activities:
                # check for 1. has activity already been completed 2. activity time slot eligibility
                if activity.pk in self.completed_activity_ids:
                    activity_status = 'completed'
                elif activity.pk in self.currently_available_activity_ids:
                    activity_status = 'available'
                elif activity.pk in self.upcoming_activity_ids:
                    activity_status = 'upcoming'
                else:
                    activity_status = 'expired'
            activity_dict['status'] = activity_status
            activity_dict['availableNow'] = activity_status == 'available'
            activity_dict['availabilities'] = [aa.to_dict() for aa in activity_availability_cache[activity.pk]]
            self.activity_dict_list.append(activity_dict)
        self.activity_dict_list.sort(key=_activity_status_sort_key)

    def expired_activities(self):
        return filter(lambda d: d['status'] == 'expired', self.activity_dict_list)

    def upcoming_activities(self):
        return filter(lambda d: d['status'] == 'upcoming', self.activity_dict_list)


class GroupScores(object):

    def __init__(self, experiment, round_data=None, groups=None, participant_group_relationship=None, start_date=None, end_date=None):
        self.round_data = experiment.current_round_data if round_data is None else round_data
        self.groups = list(experiment.groups) if groups is None else groups
        self.has_scheduled_activities = is_scheduled_activity_experiment(experiment.experiment_configuration)
        self.number_of_groups = len(self.groups)
        # { group : {average_points, total_points} }
        self.scores_dict = defaultdict(lambda: defaultdict(lambda: 0))
        self.total_participant_points = 0
        # establish date range
        self.start_date = date.today() if start_date is None else start_date
        self.end_date = self.start_date + timedelta(1) if end_date is None else end_date
        self.round_configuration = self.round_data.round_configuration
        self.show_rankings = can_view_other_groups(self.round_configuration)

        activity_points_cache = get_activity_points_cache()
        activities_performed_qs = ParticipantRoundDataValue.objects.for_round(round_data=self.round_data, parameter=get_activity_performed_parameter(), date_created__range=(self.start_date, self.end_date))
        #logger.debug("activities performed qs: %s", activities_performed_qs)
        for activity_performed_dv in activities_performed_qs:
            activity_points = activity_points_cache[activity_performed_dv.int_value]
            self.scores_dict[activity_performed_dv.participant_group_relationship.group]['total_points'] += activity_points
            if participant_group_relationship and activity_performed_dv.participant_group_relationship == participant_group_relationship:
                self.total_participant_points += activity_points
        for group in self.groups:
            group_data_dict = self.scores_dict[group]
            group_size = group.size
            total_points = group_data_dict['total_points']
            average = total_points / group_size
            group_data_dict['average_points'] = average
            #logger.debug("group data dictionary: %s", group_data_dict)

    def average_points(self, group):
        return self.scores_dict[group]['average_points']

    def total_points(self, group):
        return self.scores_dict[group]['total_points']

    def get_group_level(self, group):
        if self.has_scheduled_activities:
            return 0
        else:
            return get_footprint_level(group, self.round_data)

    def get_points_goal(self, group):
        if self.has_scheduled_activities:
            return get_group_threshold(self.round_configuration)
        else:
            return get_points_to_next_level(self.get_group_level(group))

    def is_completed(self, group):
        if self.has_scheduled_activities:
            return self.average_points(group) >= self.get_points_goal(group)
        else:
            return get_experiment_completed_dv(group, round_data=self.round_data).boolean_value


    def get_sorted_group_scores(self):
        return sorted(self.scores_dict.items(),
                      key=lambda x: x[1]['average_points'],
                      reverse=True)

    def should_advance_level(self, group, level, max_level=3):
        logger.debug("checking if group %s at level %s should advance in level on %s (%s)", group, level, self.start_date, self.scores_dict[group])
        if level <= max_level:
            return self.average_points(group) >= get_points_to_next_level(level)
        return False

    def get_group_rank(self, group):
        return self.get_group_rankings().index(group) + 1

    def get_group_rankings(self):
        if getattr(self, 'group_rankings', None) is None:
            self.group_rankings = [g[0] for g in self.get_sorted_group_scores()]
        return self.group_rankings

    def get_group_data_list(self):
        # FIXME: cache group_data?
        group_data = []
        for group in self.groups:
            group_data.append(self.to_dict(group))
        group_data.sort(key=itemgetter('averagePoints'), reverse=True)
        return group_data

    def to_dict(self, group):
        # FIXME: cache?
        return {
            'groupName': group.name,
            'groupLevel': self.get_group_level(group),
            'groupSize': group.size,
            'averagePoints': self.average_points(group),
            'totalPoints': self.total_points(group),
            'pointsToNextLevel': self.get_points_goal(group),
        }

    def create_email_messages(self, group):
        if self.has_scheduled_activities:
            return self.create_scheduled_activity_experiment_emails(group)
        else:
            # calculate total carbon savings and determine if the group should advance to the next level
            return self.create_level_experiment_emails(group)

    def create_scheduled_activity_experiment_emails(self, group):
        # FIXME: remove code duplication / redundancy between this and create_level_experiment_email_messages
        round_data = self.round_data
        logger.debug("Calculating thresholds for scheduled activity experiment")
        threshold = get_group_threshold(self.round_configuration)
        average_group_points = self.average_points(group)
        logger.debug("threshold: %s vs average group points: %s", average_group_points)
        goal_reached = average_group_points >= threshold
        # they reached their goal, set their completion flag for this round
        get_experiment_completed_dv(group, round_data=round_data).update_boolean(goal_reached)
        yesterday = date.today() - timedelta(1)
        plaintext_template = select_template(['lighterprints/email/scheduled-activity/group-summary-email.txt'])
        html_template = select_template(['lighterprints/email/scheduled-activity/group-summary-email.html'])
        experiment = group.experiment
        experimenter_email = experiment.experimenter.email
        number_of_chat_messages = ChatMessage.objects.filter(participant_group_relationship__group=group,
                                                             date_created__gte=yesterday).count()
        messages = []
        experiment_completed = not experiment.has_next_round
        for pgr in group.participant_group_relationship_set.all():
            c = Context({
                'experiment': experiment,
                'experiment_completed': experiment_completed,
                'number_of_groups': self.number_of_groups,
                'group_name': group.name,
                'group_rank': self.get_group_rank(group),
                'summary_date': yesterday,
                'show_rankings': self.show_rankings,
                'threshold': threshold,
                'average_points': average_group_points,
                'number_of_chat_messages': number_of_chat_messages,
                'individual_points': get_individual_points(pgr),
                })
            plaintext_content = plaintext_template.render(c)
            html_content = html_template.render(c)
            subject = 'Lighter Footprints Summary for %s' % yesterday
            to_address = [ experimenter_email, pgr.participant.email ]
            msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
        return messages

    def check_and_advance_level(self, group):
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
        return {'promoted': promoted, 'completed': completed, 'level': footprint_level_grdv.int_value}

    def create_level_experiment_emails(self, group):
        round_data = self.round_data
        experiment_completed_dv = get_experiment_completed_dv(group, round_data=round_data)
        already_completed = experiment_completed_dv.boolean_value
        if already_completed:
            # skip this group if it's already completed the experiment.
            return []
        level_status_dict = self.check_and_advance_level(group)
        group_summary_emails = self.create_level_based_group_summary_emails(group, round_data=round_data, **level_status_dict)
        # XXX: push into check_and_advance_level? would then have to thread experiment completed dv into method params
        # as well
        if level_status_dict['completed']:
            # store the completed flag for the group
            experiment_completed_dv.update_boolean(True)
        return group_summary_emails

    def create_level_based_group_summary_emails(self, group, level=1, **kwargs):
        logger.debug("creating level based group summary email for group %s", group)
        yesterday = date.today() - timedelta(1)
        plaintext_template = select_template(['lighterprints/email/group-summary-email.txt'])
        html_template = select_template(['lighterprints/email/group-summary-email.html'])
        experiment = group.experiment
        experimenter_email = experiment.experimenter.email
        number_of_chat_messages = ChatMessage.objects.filter(participant_group_relationship__group=group,
                                                             date_created__gte=yesterday).count()
        messages = []
        average_group_points = self.average_points(group)
        points_to_next_level = get_points_to_next_level(level)
        for pgr in group.participant_group_relationship_set.all():
            c = Context(dict({'experiment': experiment,
                              'number_of_groups': self.number_of_groups,
                              'group_name': group.name,
                              'group_level': level,
                              'group_rank': self.get_group_rank(group),
                              'summary_date': yesterday,
                              'show_rankings': self.show_rankings,
                              'points_to_next_level': points_to_next_level,
                              'average_points': average_group_points,
                              'number_of_chat_messages': number_of_chat_messages,
                              'individual_points': get_individual_points(pgr),
                              }, **kwargs))
            plaintext_content = plaintext_template.render(c)
            html_content = html_template.render(c)
            subject = 'Lighter Footprints Summary for %s' % yesterday
            to_address = [ experimenter_email, pgr.participant.email ]
            msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address)
            msg.attach_alternative(html_content, 'text/html')
            messages.append(msg)
        return messages

    def __str__(self):
        return str(self.scores_dict)


@receiver(signals.pre_system_daily_tick)
def update_active_experiments(sender, time=None, start_date=None, send_emails=True, **kwargs):
# since this happens at midnight we need to look at the previous day
    if start_date is None:
        start_date = date.today() - timedelta(1);
    active_experiments = get_active_experiments()
    logger.debug("updating active level based experiments [%s] for %s", active_experiments, start_date)
    all_messages = []
    for experiment in active_experiments:
        round_data = experiment.current_round_data
        groups = list(experiment.groups)
        group_scores = GroupScores(experiment, round_data, groups, start_date=start_date)
        for group in groups:
            messages = group_scores.create_email_messages(group)
            all_messages.extend(messages)
    if send_emails:
        logger.debug("sending messages %s", all_messages)
        mail.get_connection().send_messages(all_messages)


@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
def round_started_handler(sender, experiment=None, **kwargs):
    logger.debug("starting lighter footprints %s", experiment)
    round_data = experiment.current_round_data
    # FIXME: experiment.initialize_parameters could do some of this except for setting the default values properly
    footprint_level_parameter = get_footprint_level_parameter()
    experiment_completed_parameter = get_experiment_completed_parameter()
    experiment.initialize_data_values(
        group_parameters=(footprint_level_parameter, experiment_completed_parameter,),
        round_data=round_data,
        defaults={
            footprint_level_parameter: 1,
            experiment_completed_parameter: False
        })


class ActivityQuerySet(models.query.QuerySet):
    """
    for the moment, categorizing Activities as tiered or leveled.  Leveled activities are used in experiments, where
    groups advance in level and each level comprises a set of activities.  Tiered activities are used in the open
    lighterprints experiment, where mastering one activity can lead to another set of activities
    """
    def unlocked(self, round_configuration=None, level=1, scheduled=False):
        """
        returns a QuerySet with all unlocked Activities without checking for whether or not they are available, have
        already been performed, etc.
        """
        if scheduled:
            return self.scheduled(round_configuration)
        else:
            return self.filter(level__lte=level)

    def scheduled(self, round_configuration=None):
        if round_configuration is None:
            logger.warn("No round configuration specified, cannot report scheduled activities.")
            return []
        available_activity_ids = RoundParameterValue.objects.filter(round_configuration=round_configuration,
                parameter=get_available_activity_parameter()).values_list('int_value', flat=True)
        return self.filter(pk__in=available_activity_ids)

    def at_level(self, level=1, include_lower_levels=True, **kwargs):
        if include_lower_levels:
            return self.filter(level__lte=level)
        else:
            return self.filter(level=level)

    def total(self, pks=None, field_name='points', **kwargs):
        if not pks:
            return 0
        q = self.filter(pk__in=pks,**kwargs).aggregate(total=Sum(field_name))
        return q['total']


class ActivityManager(TreeManager, PassThroughManager):

    def scheduled(self, round_configuration, **kwargs):
        available_activity_ids = RoundParameterValue.objects.filter(round_configuration=round_configuration,
                parameter=get_available_activity_parameter()).values_list('int_value', flat=True)
        return Activity.objects.filter(pk__in=available_activity_ids)
        #return ActivityAvailability.objects.select_related('activity').filter(activity__id__in=(available_activity_ids), **kwargs).values_list('activity', flat=True)

    def already_performed(self, activity, participant_group_relationship, round_data):
        today = datetime.combine(date.today(), time())
        already_performed = participant_group_relationship.data_value_set.filter(parameter=get_activity_performed_parameter(),
                int_value=activity.id,
                round_data=round_data,
                date_created__gte=today)
        return already_performed.count() > 0

    def is_available_now(self, activity):
        current_time = datetime.now().time()
        if activity.available_all_day:
            return True
        availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
        return availabilities.count() > 0

    def is_activity_available(self, activity, participant_group_relationship, round_data):
        round_configuration = round_data.round_configuration
        unlocked_activities = []
        if is_scheduled_activity_experiment(round_configuration.experiment_configuration):
            # first query for scheduled set
            unlocked_activities = self.scheduled(round_configuration)
        else:
            unlocked_activities = Activity.objects.unlocked(level=get_footprint_level(participant_group_relationship.group, round_data))
        if activity in unlocked_activities:
            # next check if it is currently available
            currently_available = self.is_available_now(activity)
            if currently_available:
                # finally, if it is currently available, make sure they haven't already performed it
                return not self.already_performed(activity, participant_group_relationship, round_data)
        return False

    def upcoming(self, level=1, scheduled=False, round_configuration=None):
        current_time = datetime.now().time()
        if scheduled:
# find all activities scheduled for today
            return self.scheduled(round_configuration, start_time__gte=current_time)
        else:
            return self._filter_by_availability(level, start_time__gte=current_time)

    def _filter_by_availability(self, level=1, **kwargs):
        return ActivityAvailability.objects.select_related('activity').filter(models.Q(activity__level__lte=level, **kwargs)).values_list('activity', flat=True)

    def currently_available(self, level=1, current_time=None, fetch_models=False, scheduled_activities=False, **kwargs):
        ''' returns a list of available activity pks '''
        if current_time is None:
            current_time = datetime.now().time()
        activity_ids = list(self._filter_by_availability(level, start_time__lte=current_time, end_time__gte=current_time))
# add available all day activities
        activity_ids.extend(Activity.objects.filter(available_all_day=True, level__lte=level).values_list('pk', flat=True))
        if fetch_models:
            return Activity.objects.filter(pk__in=activity_ids)
        else:
            return activity_ids

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Activity(MPTTModel):
    name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=256)
    description = models.TextField()
    url = models.URLField()
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    points = models.PositiveIntegerField(default=0)
    available_all_day = models.BooleanField(default=False)
    personal_benefits = models.TextField(null=True, blank=True)
# FIXME: allow for experiment-configurable levels?
    level = models.PositiveIntegerField(default=1)
    group_activity = models.BooleanField(default=False, help_text='Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')
# currently unused
    cooldown = models.PositiveIntegerField(default=1, null=True, blank=True, help_text='How much time, in hours, must elapse before this activity can become available again')
    icon = models.ImageField(upload_to='lighterprints/activity-icons/')
# for user submitted activities
    creator = models.ForeignKey(User, null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = models.DateTimeField(default=datetime.now)
# for the "in-the-wild" app, activities unlock other sets of activities in a tree-like fashion
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children_set')
    is_public = models.BooleanField(default=False)

    objects = ActivityManager.for_queryset_class(ActivityQuerySet)()

    @property
    def label(self):
        return self.display_name if self.display_name else self.name

    @property
    def icon_name(self):
        return self.name

    @property
    def icon_url(self):
        return self.icon.url if self.icon else ""

    @property
    def time_slots(self):
        ck = 'activity_%s_timeslots' % self.pk
        cv = cache.get(ck)
        if cv is None:
            if self.available_all_day:
                cv = 'all day'
            else:
                cv = ','.join([availability.time_slot for availability in self.availability_set.all()])
            cache.set(ck, cv)
        return cv

    def is_available_for(self, participant_group_relationship, round_data):
        return Activity.objects.is_activity_available(self, participant_group_relationship, round_data)

    def to_dict(self, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'icon_url', 'icon_name', 'personal_benefits', 'points', 'time_slots')):
        ck = 'activity.%s' % self.pk
        cv = cache.get(ck)
        if cv is None:
            cv = {}
            for attr_name in attrs:
                cv[attr_name] = getattr(self, attr_name, None)
            cache.set(ck, cv)
        return cv

    def __unicode__(self):
        return u'%s: %s' % (self.label, self.points)

    class Meta:
        ordering = ['level', 'name']


def _to_hour(dt):
    return dt.strftime('%I%p').lstrip('0').lower()


class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.activity, self.start_time, self.end_time)

    @property
    def time_slot(self):
        return u'%s-%s' % (_to_hour(self.start_time), _to_hour(self.end_time))

    def to_dict(self, attrs=('start_time', 'end_time')):
        d = {}
        for attr_name in attrs:
            d[attr_name] = getattr(self, attr_name, None)
        return d

    class Meta:
        ordering = ['activity', 'start_time']


@simplecache
def get_available_activity_parameter():
    return Parameter.objects.for_round(name='available_activity')

@simplecache
def get_foursquare_category_ids(parent_category_name='Travel', subcategory_names=['Light Rail', 'Bike', 'Bus Station', 'Train Station']):
    categories = fetch_foursquare_categories()
    for parent_category in categories:
        if parent_category_name in parent_category['name']:
            return [subcategory['id'] for subcategory in parent_category['categories'] if subcategory['shortName'] in subcategory_names]


@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace=EXPERIMENT_METADATA_NAME)


@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.for_participant(name='activity_performed')


@simplecache
def get_footprint_level_parameter():
    return Parameter.objects.for_group(name='footprint_level')


@simplecache
def get_experiment_completed_parameter():
    return Parameter.objects.for_group(name='experiment_completed')


@simplecache
def get_treatment_type_parameter():
    return Parameter.objects.get(name='treatment_type')


def get_group_threshold(round_configuration, default=160):
    return round_configuration.get_parameter_value(name='threshold', default=default).int_value


def get_footprint_level_dv(group, round_data=None):
    if round_data is None:
        round_data = group.current_round_data
    return GroupRoundDataValue.objects.get(group=group, round_data=round_data, parameter=get_footprint_level_parameter())


def get_footprint_level(group, round_data=None, **kwargs):
    return get_footprint_level_dv(group, round_data=round_data, **kwargs).int_value


def get_experiment_completed_dv(group, round_data=None):
    return group.get_data_value(parameter=get_experiment_completed_parameter(), round_data=round_data)


def get_treatment_type(round_configuration=None, **kwargs):
    # XXX: if there is no treatment type we default to the compare other group condition
    return round_configuration.get_parameter_value(parameter=get_treatment_type_parameter(),
            default='COMPARE_OTHER_GROUP')


def can_view_other_groups(round_configuration=None, **kwargs):
    treatment_type = get_treatment_type(round_configuration=round_configuration)
    return 'COMPARE_OTHER_GROUP' in treatment_type.string_value

def get_active_experiments():
    """
    partition these into two tuples - level based and schedule based?
    """
    return Experiment.objects.active(experiment_metadata=get_lighterprints_experiment_metadata())


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


def get_activity_availability_cache():
    aac = cache.get('activity_availability_cache')
    if aac is None:
        aac = defaultdict(list)
        for aa in ActivityAvailability.objects.select_related('activity').all():
            aac[aa.activity.pk].append(aa)
        cache.set('activity_availability_cache', aac)
    return aac


def do_activity(activity, participant_group_relationship):
    round_data = participant_group_relationship.current_round_data
    if activity.is_available_for(participant_group_relationship, round_data):
        logger.debug("performing available activity %s", activity)
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                                                        participant_group_relationship=participant_group_relationship,
                                                        round_data=round_data,
                                                        int_value=activity.pk,
                                                        submitted=True)


def get_performed_activity_ids(participant_group_relationship):
    return participant_group_relationship.data_value_set.filter(parameter=get_activity_performed_parameter()).values_list('id', flat=True)


def get_points_to_next_level(current_level):
    """ returns the number of average points needed to advance to the next level """
    if current_level == 1:
        return 50
    elif current_level == 2:
        return 125
    elif current_level == 3:
        return 225


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
    like_target_ids = Like.objects.filter(participant_group_relationship=participant_group_relationship).values_list('target_data_value', flat=True)
    comment_target_ids = Comment.objects.filter(participant_group_relationship=participant_group_relationship).values_list('target_data_value', flat=True)
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
            data['date_performed'] = prdv.date_created
            pgr = prdv.participant_group_relationship
            data['participant_number'] = pgr.participant_number
            data['participant_name'] = pgr.full_name
            data['participant_group_id'] = pgr.pk
            data['activity_performed_id'] = prdv.pk
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


def get_individual_points(participant_group_relationship, end_date=None):
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(1)
    pks = ParticipantRoundDataValue.objects.filter(participant_group_relationship=participant_group_relationship,
                                                   date_created__range=(start_date, end_date),
                                                   parameter=get_activity_performed_parameter()).values_list('int_value', flat=True)
    # XXX: assumes that an Activity can only be performed once per round (day)
    return Activity.objects.total(pks=pks)



