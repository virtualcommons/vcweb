from django.db import models
from django.db.models import Sum, Q
from vcweb.core import signals, simplecache
from vcweb.core.models import (Experiment, ExperimentMetadata, Experimenter,
        GroupRoundDataValue, ParticipantRoundDataValue, Parameter)
from django.dispatch import receiver
from decimal import Decimal
import datetime

import logging
logger = logging.getLogger(__name__)

class Activity(models.Model):
    name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=256)
    description = models.TextField()
    url = models.URLField()
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    available_all_day = models.BooleanField(default=False)
# FIXME: allow for experiment-configurable levels?
    level = models.PositiveIntegerField(default=1)
    group_activity = models.BooleanField(default=False, help_text='Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')
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

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.savings)

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    available_start_time = models.TimeField(null=True, blank=True)
    available_end_time = models.TimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.activity, self.available_start_time, self.available_end_time)

    class Meta:
        ordering = ['activity', 'available_start_time']

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
def get_carbon_footprint_level_parameter():
    return Parameter.objects.get(name='carbon_footprint_level')

def get_active_experiments():
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))

def available_activities(activity=None):
    current_time = datetime.datetime.now().time()
    filter_dict = dict(available_start_time__lte=current_time,
            available_end_time__gte=current_time)
    if activity is not None:
        filter_dict['activity'] = activity
    logger.debug("filtering with filter dict %s", filter_dict)
    return ActivityAvailability.objects.select_related(depth=1).filter(Q(**filter_dict) | Q(activity__available_all_day=True))

def is_activity_available(activity=None, participant_group_relationship=None, **kwargs):
    if activity is None:
        logger.debug("cannot check availability for non activity")
        return False
# how often can a participant participate in an activity?
# whenever it falls within the ActivityAvailability schedule and if the participant
# hasn't already performed this activity during this cycle.
    now = datetime.datetime.now()
    current_time = now.time()
    availabilities = ActivityAvailability.objects.filter(Q(activity=activity, activity__available_all_day=True) | Q(available_start_time__lte=current_time, available_end_time__gte=current_time))
# FIXME: check if this participant has already participated in this activity
    data_value_set = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
            participant_group_relationship=participant_group_relationship,
            submitted=True,
            date_created__lte=now,
            date_created__gte=now)
    return availabilities.count() > 0 and data_value_set.count() == 0

def do_activity(activity=None, participant_group_relationship=None):
    if is_activity_available(activity, participant_group_relationship):
        round_data = participant_group_relationship.group.current_round_data
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                round_data=round_data,
                # FIXME: use activity unique name instead?
                value=activity.pk
                )

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, **kwargs):
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.group_set.all():
            grdv = GroupRoundDataValue.objects.get(group=group, parameter__name='carbon_footprint_level')
            if should_advance_level(group, grdv.value):
# advance group level
                grdv.value = min(grdv.value + 1, 3)
                grdv.save()

@receiver(signals.round_started)
def round_started_handler(sender, experiment=None, **kwargs):
    if sender != get_lighterprints_experiment_metadata().pk:
        logger.debug("received invalid signal from sender %s", sender)
        return
    # FIXME: See if we can push this logic up to core..
    logger.debug("initializing lighter prints")
    experiment.initialize_parameters(
            group_parameters = [get_carbon_footprint_level_parameter()],
            participant_parameters = [get_activity_performed_parameter()]
            )

def get_daily_carbon_savings(group):
# grab all of yesterday's participant data values
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(1)
    total_savings = Decimal(0.0)
    for activity_performed_dv in group.get_participant_data_values(parameter_name='activity_performed').filter(date_created__gte=yesterday):
        logger.debug("%s", activity_performed_dv)
        activity = Activity.objects.get(pk=activity_performed_dv.value)
        total_savings += activity.savings
    #total = participant_data_values.aggregate(total=Sum('int_value'))['total']
    logger.debug("total carbon savings: %s", total_savings)
    return total_savings


def should_advance_level(group, level):
    if level < 3:
        daily_carbon_savings = get_daily_carbon_savings(group)
        return daily_carbon_savings > level * 10
    return False

