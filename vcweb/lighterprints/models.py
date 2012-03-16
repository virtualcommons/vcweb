from django.db import models
from django.db.models import Q
from vcweb.core import signals, simplecache, enum
from vcweb.core.models import (Experiment, ExperimentMetadata, Experimenter,
        GroupRoundDataValue, ParticipantRoundDataValue, Parameter)
from django.dispatch import receiver
import collections
import datetime
import logging
logger = logging.getLogger(__name__)

ActivityStatus = enum('AVAILABLE', 'COMPLETED', 'UNAVAILABLE')

class Activity(models.Model):
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

    @property
    def label(self):
        return self.display_name if self.display_name else self.name

    @property
    def icon_name(self):
        return self.name

    @property
    def icon_url(self):
        return self.icon.url if self.icon else ""

    def to_dict(self, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'icon_url', 'personal_benefits', 'points')):
        activity_as_dict = {}
        for attr_name in attrs:
            activity_as_dict[attr_name] = getattr(self, attr_name, None)
        return activity_as_dict

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.savings)

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.activity, self.start_time, self.end_time)

    @property
    def time_slot(self):
        return u'%s - %s' % (self.start_time.strftime('%I:%M %p'), self.end_time.strftime('%I:%M %p'))

    def to_dict(self, attrs=('start_time', 'end_time')):
        d = {}
        for attr_name in attrs:
            d[attr_name] = getattr(self, attr_name, None)
        return d

    class Meta:
        ordering = ['activity', 'start_time']

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

def create_activity_performed_parameter(experimenter=None):
    if experimenter is None:
        experimenter = Experimenter.objects.get(pk=1)
    parameter, created = Parameter.objects.get_or_create(name='activity_performed', scope=Parameter.PARTICIPANT_SCOPE, type='int',
            creator=experimenter, experiment_metadata=get_lighterprints_experiment_metadata())
    if created: logger.debug("created activity performed parameter %s", parameter)
    return parameter

@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.get(name='activity_performed')

@simplecache
def get_footprint_level_parameter():
    return Parameter.objects.get(name='footprint_level')

def get_footprint_level(group):
    return GroupRoundDataValue.objects.get(group=group, parameter=get_footprint_level_parameter())

def get_active_experiments():
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))


# returns a tuple of (flattened_activities list + activity_by_level dict)
def get_all_available_activities(participant_group_relationship, all_activities=None):
    if all_activities is None:
        all_activities = Activity.objects.all()
    flattened_activities = []
    activity_by_level = collections.defaultdict(list)

    for activity in all_activities:
        activity_by_level[activity.level].append(activity)
        activity_as_dict = activity.to_dict()
        try:
            activity_as_dict['availabilities'] = [availability.to_dict() for availability in ActivityAvailability.objects.filter(activity=activity)]
            activity_as_dict['available'] = is_activity_available(activity, participant_group_relationship)
            activity_as_dict['time_slots'] = ','.join([av.time_slot for av in activity.availability_set.all()])
        except Exception as e:
            logger.debug("failed to get authenticated activity list: %s", e)
        flattened_activities.append(activity_as_dict)
    return (flattened_activities, activity_by_level)

def available_activities(activity=None):
    current_time = datetime.datetime.now().time()
    available_time_slot = dict(start_time__lte=current_time, end_time__gte=current_time)
    if activity is not None:
        available_time_slot['activity'] = activity
    activities = [activity_availability.activity for activity_availability in ActivityAvailability.objects.select_related(depth=1).filter(Q(**available_time_slot))]
    logger.debug("activities: %s", activities)
    activities.extend(Activity.objects.filter(available_all_day=True))
    return activities

def check_activity_availability(activity, participant_group_relationship, **kwargs):
# how often can a participant participate in an activity?
# whenever it falls within the ActivityAvailability schedule and if the participant
# hasn't already performed this activity during this cycle.
    logger.debug("checking if %s is available for %s", activity, participant_group_relationship)
    level = get_footprint_level(participant_group_relationship.group).value
    if activity.level > level:
        logger.debug("activity %s had larger level (%s) than group level (%s)", activity, activity.level, level)
        return ActivityStatus.UNAVAILABLE
    elif activity.available_all_day:
        # check if they've done it already today, check if the combine is necessary
        today = datetime.datetime.combine(datetime.date.today(), datetime.time())
        already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                int_value=activity.id,
                date_created__gt=today)
        logger.debug("activity is available all day, was it already performed? %s", already_performed)
        return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED
    else:
        now = datetime.datetime.now()
        current_time = now.time()
        # FIXME: check if this participant has already participated in this activity within this particular interval (for all
        # day, today, for time slots, during this particular time slot). There should only be one availability
        try:
            logger.debug("checking availability set %s", activity.availability_set.all())
            availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
            earliest_start_time = datetime.datetime.combine(datetime.date.today(), availabilities[0].start_time)
            logger.debug("earliest start time: %s", earliest_start_time)
            already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                    participant_group_relationship=participant_group_relationship,
                    int_value=activity.pk,
                    date_created__range=(earliest_start_time, now))
            return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED
        except Exception as e:
            logger.debug("exception while checking if this activity had already been performed by this participant: %s", e)
            return ActivityStatus.UNAVAILABLE

def is_activity_available(activity, participant_group_relationship):
    return check_activity_availability(activity, participant_group_relationship) == ActivityStatus.AVAILABLE

def do_activity(activity, participant_group_relationship):
    if is_activity_available(activity, participant_group_relationship):
        logger.debug("activity %s was available", activity)
        round_data = participant_group_relationship.group.current_round_data
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                round_data=round_data,
                # FIXME: use activity unique name instead?
                value=activity.pk,
                submitted=True
                )

def get_performed_activity_ids(participant_group_relationship):
    return [prdv.pk for prdv in participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter())]

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, **kwargs):
    logger.debug("updating active experiments")
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.group_set.all():
            footprint_level_grdv = get_footprint_level(group)
            if should_advance_level(group, footprint_level_grdv.value):
# advance group level
                footprint_level_grdv.value = min(footprint_level_grdv.value + 1, 3)
                footprint_level_grdv.save()

@receiver(signals.round_started)
def round_started_handler(sender, experiment=None, **kwargs):
    if sender != get_lighterprints_experiment_metadata().pk:
        logger.debug("received invalid signal from sender %s", sender)
        return
    # FIXME: See if we can push this logic up to core..
    current_round_data = experiment.current_round_data
    footprint_level_parameter = get_footprint_level_parameter()
# only create the carbon footprint level parameter, the participant activity performed data values will be created each
# time.
    for group in experiment.group_set.all():
        footprint_level_grdv = current_round_data.group_data_value_set.create(group=group, parameter=footprint_level_parameter)
        footprint_level_grdv.value = 1
        footprint_level_grdv.save()

def average_points_per_person(group):
    return get_group_points_summary(group)[0]

# returns a tuple of the average points per person and the total savings for
# the given group
def get_group_points_summary(group):
    # grab all of yesterday's participant data values, starting at 00:00:00 (midnight)
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(1)
    total_points = 0
    for activity_performed_dv in group.get_participant_data_values(parameter=get_activity_performed_parameter()).filter(date_created__gte=yesterday):
        activity = Activity.objects.get(pk=activity_performed_dv.value)
        total_points += activity.points
    average = total_points / group.size
    logger.debug("total carbon savings: %s divided by %s members = %s per person", total_points, group.size,
            average)
    return (average, total_points)

def points_to_next_level(level, level_multiplier=100):
    return level * level_multiplier

def should_advance_level(group, level, max_level=3):
    if level < max_level:
        return average_points_per_person(group) >= points_to_next_level(level)
    return False

