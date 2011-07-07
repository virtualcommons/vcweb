from django.db import models
from django.db.models import Sum
from vcweb.core import signals, simplecache
from vcweb.core.models import Experiment, ExperimentMetadata, Experimenter, GroupRoundDataValue, Parameter
from django.dispatch import receiver
import datetime

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
        return self.icon.url

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.savings)

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity)
    available_start_time = models.TimeField(null=True, blank=True)
    available_end_time = models.TimeField(null=True, blank=True)

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

@simplecache
def create_activity_performed_parameter(experimenter=None):
    if experimenter is None:
        experimenter = Experimenter.objects.get(pk=1)
    parameter, created = Parameter.objects.get_or_create(name='activity_performed', scope=Parameter.PARTICIPANT_SCOPE, type='int',
            creator=experimenter, experiment_metadata=get_lighterprints_experiment_metadata())
    return parameter

@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.get(name='activity_performed')

def get_active_experiments():
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, **kwargs):
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.groups.all():
            grdv = GroupRoundDataValue.objects.get(group=group, name='carbon_footprint_level')
            if should_advance_level(group, grdv.value):
# advance group level
                grdv.value = min(grdv.value + 1, 3)
                grdv.save()


def get_daily_carbon_savings(group):
# grab all of yesterday's participant data values
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(1)
    participant_data_values = group.get_participant_data_values().filter(date_created__gte=yesterday)
    participant_data_values.aggregate(total=Sum('value'))
    return participant_data_values['total']


def should_advance_level(group, level):
    if level < 3:
        daily_carbon_savings = get_daily_carbon_savings(group)
        return daily_carbon_savings > level * 10
    return False

