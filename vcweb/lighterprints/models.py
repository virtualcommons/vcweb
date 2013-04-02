from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.db.models import Sum
from django.dispatch import receiver
from django.template import Context
from django.template.loader import select_template
from django.utils.timesince import timesince
from django.utils.translation import ugettext_lazy as _
from functools import partial
from model_utils.managers import PassThroughManager
from vcweb.core import signals, simplecache, enum
from vcweb.core.models import (Experiment, ExperimentMetadata, GroupRoundDataValue, RoundParameterValue, ParticipantGroupRelationship, ParticipantRoundDataValue, Parameter, User, Comment, Like, ChatMessage)
from vcweb.core.services import fetch_foursquare_categories
import collections
from datetime import datetime, date, time, timedelta
from mptt.models import MPTTModel, TreeForeignKey, TreeManager
from lxml import etree

import logging
import re
import string
logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = intern('lighterprints')

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, start=None, send_emails=True, **kwargs):
# since this happens at midnight we need to look at the previous day
    if start is None:
        start = date.today() - timedelta(1);
    active_experiments = get_active_experiments()
    logger.debug("updating active experiments [%s] for %s", active_experiments, start)
    messages = []
    for experiment in active_experiments:
        # calculate total carbon savings and decide if they move on to the next level
        round_data = experiment.current_round_data
        for group in experiment.groups:
            promoted = False
            completed = False
            footprint_level_grdv = get_footprint_level_dv(group, round_data=round_data)
            current_level = footprint_level_grdv.value
            if should_advance_level(group, footprint_level_grdv.int_value, start, round_data=round_data):
                # group was promoted
                promoted = True
                next_level = min(current_level + 1, 3)
                footprint_level_grdv.int_value = next_level
                footprint_level_grdv.save()
                if current_level == 3:
                    completed = True
# FIXME: store another group data parameter that says they've completed the experiment?
            experiment_completed_dv = get_experiment_completed_dv(group, round_data=round_data)
            already_completed = experiment_completed_dv.boolean_value
            if not already_completed:
                group_summary_emails = create_group_summary_emails(group, footprint_level_grdv.value, promoted=promoted, completed=completed, round_data=round_data)
                messages.extend(group_summary_emails)
                if completed:
                    experiment_completed_dv.boolean_value = True
                    experiment_completed_dv.save()
    logger.debug("about to send nightly summary emails (%s): %s", send_emails, messages)
    if send_emails:
        mail.get_connection().send_messages(messages)

@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
def round_started_handler(sender, experiment=None, **kwargs):
    logger.debug("starting lighter footprints %s", experiment)
    round_data = experiment.current_round_data
    # FIXME: experiment.initialize_parameters could do some of this except for setting the default values properly
    footprint_level_parameter = get_footprint_level_parameter()
    experiment_completed_parameter = get_experiment_completed_parameter()
    experiment.initialize_data_values(
            group_parameters=( footprint_level_parameter, experiment_completed_parameter, ),
            round_data=round_data,
            defaults={
                footprint_level_parameter: 1,
                experiment_completed_parameter: False
                }
            )


ActivityStatus = enum('AVAILABLE', 'COMPLETED', 'UNAVAILABLE')

class ActivityQuerySet(models.query.QuerySet):
    """
    for the moment, categorizing Activities as tiered or leveled.  Leveled activities are used in experiments, where
    groups advance in level and each level comprises a set of activities.  Tiered activities are used in the open
    lighterprints experiment, where mastering one activity can lead to another set of activities
    """
    def at_level(self, level=1, include_lower_levels=True, **kwargs):
        if include_lower_levels:
            return self.filter(level__lte=level)
        else:
            return self.filter(level=level)

    def total(self, pks=None, field_name='points', **kwargs):
        logger.debug("getting total for pks %s", pks)
        if not pks:
            return 0
        q = self.filter(pk__in=pks,**kwargs).aggregate(total=Sum(field_name))
        return q['total']

class ActivityManager(TreeManager, PassThroughManager):
    def upcoming(self, level=1):
        current_time = datetime.now().time()
        return self._filter_by_availability(level, start_time__gte=current_time)

    def _filter_by_availability(self, level=1, **kwargs):
        return [aa.activity for aa in ActivityAvailability.objects.select_related('activity').filter(models.Q(**kwargs)) if aa.activity.level <= level]

    def currently_available(self, level=1, **kwargs):
        current_time = datetime.now().time()
        activities = self._filter_by_availability(level, start_time__lte=current_time, end_time__gte=current_time)
# add available all day activities
        activities.extend(Activity.objects.filter(available_all_day=True, level__lte=level))
        return activities

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
                cv = 'available all day'
            else:
                cv = ','.join([availability.time_slot for availability in self.availability_set.all()])
            cache.set(ck, cv)
        return cv

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
        return u'%s' % self.label

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.activity, self.start_time, self.end_time)

    def _to_hour(self, dt):
        return dt.strftime('%I%p').lstrip('0').lower()

    @property
    def time_slot(self):
        return u'%s-%s' % (self._to_hour(self.start_time), self._to_hour(self.end_time))

    def to_dict(self, attrs=('start_time', 'end_time')):
        d = {}
        for attr_name in attrs:
            d[attr_name] = getattr(self, attr_name, None)
        return d

    class Meta:
        ordering = ['activity', 'start_time']

'''
API / model utility methods
'''
@simplecache
def get_foursquare_category_ids(parent_category_name='Travel', subcategory_names=['Light Rail', 'Bike', 'Bus Station', 'Train Station']):
    categories = fetch_foursquare_categories()
    for parent_category in categories:
        if parent_category_name in parent_category['name']:
            return [subcategory['id'] for subcategory in parent_category['categories'] if subcategory['shortName'] in subcategory_names]

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

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

def get_footprint_level_dv(group, round_data=None):
    if round_data is None:
        round_data = group.current_round_data
    return GroupRoundDataValue.objects.get(group=group, round_data=round_data, parameter=get_footprint_level_parameter())

def get_footprint_level(group, **kwargs):
    return get_footprint_level_dv(group, **kwargs).int_value

def get_experiment_completed_dv(group, round_data=None):
    if round_data is None:
        round_data = group.current_round_data
    return GroupRoundDataValue.objects.get(group=group, round_data=round_data,
            parameter=get_experiment_completed_parameter())

def is_experiment_completed(group, **kwargs):
    return get_experiment_completed_dv(group, **kwargs).boolean_value

def get_treatment_type(round_configuration=None, **kwargs):
    try:
        return RoundParameterValue.objects.get(round_configuration=round_configuration, parameter=get_treatment_type_parameter())
    except RoundParameterValue.DoesNotExist:
        return None

def can_view_other_groups(round_configuration=None, **kwargs):
    treatment_type = get_treatment_type(round_configuration=round_configuration)
# XXX: if there is no treatment type we default to the compare other group condition
    return (treatment_type is None) or ('COMPARE_OTHER_GROUP' in treatment_type.string_value)

def get_active_experiments():
    return Experiment.objects.active(experiment_metadata=get_lighterprints_experiment_metadata())

def get_activity_status_dict(participant_group_relationship, activities, group_level=1):
    today = datetime.combine(date.today(), time())
    available_activities = Activity.objects.currently_available(participant_group_relationship=participant_group_relationship, level=group_level)
# filter out all activities that have already been performed today (activities may only be performed once a day)
    performed_activity_data_values = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter(),
            int_value__in=[activity.id for activity in available_activities],
            date_created__gte=today)
    upcoming_activities = Activity.objects.upcoming(level=group_level)
    # XXX: data value's int_value stores the fk directly, using .value does a fk lookup to restore the full entity
    # which we don't need
    performed_activity_ids = [padv.int_value for padv in performed_activity_data_values]
    available_activity_ids = [activity.pk for activity in available_activities if activity.pk not in performed_activity_ids]
    upcoming_activity_ids = [activity.pk for activity in upcoming_activities]
    status_dict = {}
    for activity in activities:
        if activity.pk in performed_activity_ids:
            status = 'completed-challenge disabled'
        elif activity.pk in available_activity_ids:
            status = 'perform-challenge'
        elif activity.pk in upcoming_activity_ids:
            status = 'upcoming-challenge disabled'
        elif activity.level > group_level:
            status = 'locked-challenge disabled'
        else:
            status = 'expired-challenge disabled'
        status_dict[activity.pk] = status

    return status_dict

def _activity_status_sort_key(activity_dict):
    s = activity_dict['status']
    if 'perform' in s:
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
        aac = collections.defaultdict(list)
        for aa in ActivityAvailability.objects.select_related('activity').all():
            aac[aa.activity.pk].append(aa)
        cache.set('activity_availability_cache', aac)
    return aac

# returns a tuple of a (list of activity objects converted to dicts and an activity_by_level list of lists (level -> list of activity
# objects converted to dicts).
def get_all_activities_tuple(participant_group_relationship, activities=None, group_level=1):
    if activities is None:
        activities = Activity.objects.all()
    activity_dict_list = []
    level_activity_list = []
    activity_statuses = get_activity_status_dict(participant_group_relationship, activities, group_level)
    #available_activities = get_available_activities(participant_group_relationship)
    #available_activity_ids = [activity.pk for activity in available_activities]
    activity_availability_cache = get_activity_availability_cache()

    for activity in activities:
        activity_dict = activity.to_dict()
        level = activity.level
        try:
            activity_dict['availabilities'] = [aa.to_dict() for aa in activity_availability_cache[activity.pk]]
            activity_dict['locked'] = (group_level < level)
            activity_status = activity_statuses[activity.pk]
            activity_dict['availableNow'] = "perform-challenge" in activity_status
            activity_dict['completed'] = 'completed-challenge' in activity_status
            activity_dict['expired'] = 'expired-challenge' in activity_status
            activity_dict['upcoming'] = 'upcoming-challenge' in activity_status
            activity_dict['status'] = activity_status
        except Exception as e:
            logger.debug("failed to get authenticated activity list: %s", e)
        activity_dict_list.append(activity_dict)
        # XXX: assumes activity list is ordered by level
        if level > len(level_activity_list):
            level_activity_list.append([])
        level_activity_list[level-1].append(activity_dict)
    activity_dict_list.sort(key=_activity_status_sort_key)
    return (activity_dict_list, level_activity_list)

def get_available_activities(participant_group_relationship=None, ignore_time=False):
    if participant_group_relationship is None:
        logger.warn("asking for available activities with no participant, returning all activities")
        return Activity.objects.all()
    else:
        logger.debug("requesting available activities for pgr %s (%d)", participant_group_relationship, participant_group_relationship.pk)
        # FIXME: push this logic into the manager / queryset?
        experiment = participant_group_relationship.group.experiment
        group_level = get_footprint_level(participant_group_relationship.group, round_data=experiment.current_round_data)
        if ignore_time:
            # don't worry about the time, just return all activities at this participant's group level
            return Activity.objects.at_level(group_level)

        today = datetime.combine(date.today(), time())
        available_activities = Activity.objects.currently_available(participant_group_relationship=participant_group_relationship, level=group_level)
# filter out all activities that have already been performed today (activities may only be performed once a day)
        performed_activity_data_values = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter(),
                int_value__in=[activity.id for activity in available_activities],
                date_created__gte=today)
        # XXX: data value's int_value stores the fk directly, using .value does a fk lookup to restore the full entity
        # which we don't need
        performed_activity_ids = [padv.int_value for padv in performed_activity_data_values]
        return [activity for activity in available_activities if activity.id not in performed_activity_ids]

def check_already_performed_today(activity, participant_group_relationship):
    today = datetime.combine(date.today(), time())
    already_performed = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter(),
            int_value=activity.id,
            date_created__gt=today)
    return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED


def check_activity_availability(activity, participant_group_relationship, **kwargs):
    '''
    FIXME: see if we can simplify or split up
    how often can a participant participate in an activity? whenever it falls within the ActivityAvailability schedule
    and if the participant hasn't already performed this activity during a one-day cycle (which begins at midnight)
    '''
    level = get_footprint_level(participant_group_relationship.group, **kwargs)
    if activity.level > level:
        logger.debug("activity %s had larger level (%s) than group level (%s)", activity, activity.level, level)
        return ActivityStatus.UNAVAILABLE
    elif activity.available_all_day:
        # check if they've done it already today, check if the combine is necessary
        activity_status = check_already_performed_today(activity, participant_group_relationship)
        logger.debug("activity is available all day, was it already performed? %s", activity_status)
        return activity_status
    else:
        now = datetime.now()
        current_time = now.time()
        # FIXME: check if this participant has already participated in this activity within this particular interval (for all
        # day, today, for time slots, during this particular time slot). There should only be one availability
        try:
            logger.debug("checking availability set %s", activity.availability_set.all())
            availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
            if availabilities.count() > 0:
                earliest_start_time = datetime.combine(date.today(), availabilities[0].start_time)
                logger.debug("earliest start time: %s", earliest_start_time)
                already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                        participant_group_relationship=participant_group_relationship,
                        int_value=activity.pk,
                        date_created__range=(earliest_start_time, now))
                return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED
        except Exception as e:
            logger.debug("exception while checking if this activity had already been performed by this participant: %s", e)
# default behavior is for the activity to be unavailable
    return ActivityStatus.UNAVAILABLE

def is_activity_available(activity, participant_group_relationship, **kwargs):
    return check_activity_availability(activity, participant_group_relationship, **kwargs) == ActivityStatus.AVAILABLE

def do_activity(activity, participant_group_relationship):
    round_data = participant_group_relationship.current_round_data
    if is_activity_available(activity, participant_group_relationship, round_data=round_data):
        logger.debug("activity %s was available", activity)
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                round_data=round_data,
                # FIXME: use activity unique name instead?
                value=activity.pk,
                submitted=True
                )

def get_performed_activity_ids(participant_group_relationship):
    return participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter()).values_list('id', flat=True)

def get_activity_points_cache():
    cv = 'activity_points_cache'
    activity_points_cache = cache.get(cv)
    if activity_points_cache is None:
        activity_points_cache = dict([(a.pk, a.points) for a in Activity.objects.all()])
        #cache.set(cv, activity_points_cache, timedelta(days=1).total_seconds())
        cache.set(cv, activity_points_cache, 86400)
    return activity_points_cache

def average_points_per_person(group, start=None, end=None, round_data=None):
    return get_group_score(group, start=start, end=end, round_data=round_data)[0]

# cache activity points
# returns a tuple of the average points per person and the total points for
# the given group
def get_group_score(group, start=None, end=None, participant_group_relationship=None, round_data=None, **kwargs):
    activity_points_cache = get_activity_points_cache()
    # establish date range
    # grab all of yesterday's participant data values, starting at 00:00:00 (midnight)
    total_group_points = 0
    total_participant_points = 0
    if start is None:
        start = date.today()
    if end is None:
        end = start + timedelta(1)
    if round_data is None:
        round_data = group.current_round_data
    activities_performed_qs = ParticipantRoundDataValue.objects.for_group(group, parameter=get_activity_performed_parameter(), round_data=round_data, date_created__range=(start, end))

    for activity_performed_dv in activities_performed_qs:
        logger.debug("checking activity performed: %s", activity_performed_dv)
        activity_points = activity_points_cache[activity_performed_dv.int_value]
        total_group_points += activity_points
        if activity_performed_dv.participant_group_relationship == participant_group_relationship:
            total_participant_points += activity_points
    group_size = group.size
    average = total_group_points / group_size
    logger.debug("total carbon savings: %s divided by %s members = %s per person", total_group_points, group_size, average)
    return (average, total_group_points, total_participant_points)

def get_points_to_next_level(current_level):
    ''' returns the number of average points needed to advance to the next level '''
    if current_level == 1:
        return 50
    elif current_level == 2:
        return 125
    elif current_level == 3:
        return 225

def should_advance_level(group, level, start=None, end=None, round_data=None, max_level=4):
    logger.debug("checking if group %s at level %s should advance in level on %s", group, level, start)
    if level < max_level:
        return average_points_per_person(group, start=start, end=end, round_data=round_data) >= get_points_to_next_level(level)
    return False

def get_activity_performed_counts(participant_group_relationship, activity_performed_parameter=None):
    if activity_performed_parameter is None:
        activity_performed_parameter = get_activity_performed_parameter()
    return participant_group_relationship.participant_data_value_set.filter(parameter=activity_performed_parameter).values('int_value').order_by().annotate(count=models.Count('int_value'))

def get_time_remaining():
    '''
    returns the hours and minutes till midnight
    '''
    now = datetime.now()
    midnight = datetime.combine(date.today() + timedelta(1), time())
    time_remaining = midnight - now
    seconds_left = time_remaining.seconds
    total_minutes_left = seconds_left / 60
    hours_left = total_minutes_left / 60
# pad minutes to have a leading 0 for single digits
    minutes = str(total_minutes_left % 60).zfill(2)
    return (hours_left, minutes)

def get_group_activity(participant_group_relationship, limit=None):
    group = participant_group_relationship.group
    all_activity = []
    chat_messages = []
# FIXME: consider using InheritanceManager or manually selecting likes, comments, chatmessages, activities performed to
# avoid n+1 selects when doing a to_dict
    data_values = ParticipantRoundDataValue.objects.for_group(group)
    own_likes = Like.objects.select_related('target_data_value').filter(participant_group_relationship=participant_group_relationship)
    like_target_ids = [l.target_data_value.pk for l in own_likes]
    own_comments = Comment.objects.select_related('target_data_value').filter(participant_group_relationship=participant_group_relationship)
    comment_target_ids = [c.target_data_value.pk for c in own_comments]
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
    return (all_activity, chat_messages)

def abbreviated_timesince(date):
    s = timesince(date)
    s = re.sub(r'\sdays?', 'd', s)
    s = re.sub(r'\sminutes?', 'm', s)
    s = re.sub(r'\shours?', 'h', s)
    s = re.sub(r'\sweeks?', 'w', s)
    s = re.sub(r'\smonths?', 'mo', s)
    return s.replace(',', '')

def create_group_summary_emails(group, level, promoted=False, completed=False, round_data=None):
    logger.debug("creating group summary email for group %s", group)
# FIXME: need some logic to select an email template based on the treatment type, or push into the template itself
    plaintext_template = select_template(['lighterprints/email/group-summary-email.txt'])
    html_template = select_template(['lighterprints/email/group-summary-email.html'])
    experiment = group.experiment
    experimenter_email = experiment.experimenter.email
    yesterday = date.today() - timedelta(1)
    number_of_chat_messages = ChatMessage.objects.filter(participant_group_relationship__group=group, date_created__gte=yesterday).count()
    messages = []
    for pgr in group.participant_group_relationship_set.all():
        c = Context({
            'experiment': experiment,
            'group_name': group.name,
            'summary_date': yesterday,
            'completed': completed,
            'promoted': promoted,
            'group_level': level,
            'points_to_next_level': get_points_to_next_level(level),
            'average_group_points': average_points_per_person(group, start=yesterday),
            'number_of_chat_messages': number_of_chat_messages,
            'individual_points': get_individual_points(pgr),
                })
        plaintext_content = plaintext_template.render(c)
        html_content = html_template.render(c)
        subject = 'Lighter Footprints Summary for %s' % yesterday
        to_address = [ experimenter_email, pgr.participant.email ]
# FIXME: remove in production
#    to_address.extend(['marco.janssen@asu.edu', 'shelby.manney@asu.edu', 'allen.lee@asu.edu', 'rsinha@asu.edu'])
        msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address)
        msg.attach_alternative(html_content, 'text/html')
        messages.append(msg)
    return messages

def get_individual_points(participant_group_relationship, end_date=None):
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(1)
    prdvs = ParticipantRoundDataValue.objects.filter(participant_group_relationship=participant_group_relationship,
            date_created__range=(start_date, end_date), parameter=get_activity_performed_parameter())
    pks = prdvs.values_list('int_value', flat=True)
    # XXX: assumes that an Activity can only be performed once per round (day)
    return Activity.objects.total(pks=pks)
    # this generates a query per participant round data value, very inefficient
    #return sum(prdv.value.points for prdv in prdvs)
