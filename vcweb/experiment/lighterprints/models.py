import logging
import sys
from collections import defaultdict
from datetime import datetime

from django.core.cache import cache
from django.db import models
from django.db.models import Sum
from django.utils.translation import ugettext_lazy as _
from mptt.models import (MPTTModel, TreeForeignKey, TreeManager)

from vcweb.core import simplecache
from vcweb.core.models import (ExperimentMetadata, GroupRoundDataValue, Parameter, User)

logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = sys.intern('lighterprints')


def get_activity_points_cache():
    cv = 'activity_points_cache'
    activity_points_cache = cache.get(cv)
    if activity_points_cache is None:
        activity_points_cache = dict(Activity.objects.values_list('pk', 'points'))
        cache.set(cv, activity_points_cache, 86400)
    return activity_points_cache


def get_activity_availability_cache():
    cv = 'activity_availability_cache'
    cached_availability = cache.get(cv)
    if cached_availability is None:
        cached_availability = defaultdict(list)
        for aa in ActivityAvailability.objects.select_related('activity').all():
            cached_availability[aa.activity.pk].append(aa.to_dict())
        cache.set(cv, cached_availability, 86400)
    return cached_availability


def is_level_based_experiment(experiment=None, treatment_type=None, experiment_configuration=None):
    if treatment_type is None:
        treatment_type = get_treatment_type(experiment, experiment_configuration).string_value
    return treatment_type == 'LEVEL_BASED'


def is_scheduled_activity_experiment(experiment=None, treatment_type=None, experiment_configuration=None):
    if treatment_type is None:
        treatment_type = get_treatment_type(experiment, experiment_configuration).string_value
    return treatment_type != 'LEVEL_BASED'


def is_high_school_treatment(experiment=None, treatment_type=None, experiment_configuration=None):
    if treatment_type is None:
        treatment_type = get_treatment_type(experiment, experiment_configuration).string_value
    return treatment_type == 'HIGH_SCHOOL'


def is_community_treatment(experiment=None, treatment_type=None, experiment_configuration=None):
    if treatment_type is None:
        treatment_type = get_treatment_type(experiment, experiment_configuration).string_value
    return treatment_type == 'COMMUNITY'


class ActivityQuerySet(models.query.QuerySet):

    """
    Provides query set methods for finding all unlocked activities, scheduled activities

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
        available_activity_ids = round_configuration.parameter_value_set.filter(
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
        q = self.filter(pk__in=pks, **kwargs).aggregate(total=Sum(field_name))
        return q['total']


class ActivityManager(TreeManager, models.Manager):

    def already_performed(self, activity, participant_group_relationship, round_data):
        # today = datetime.combine(date.today(), time())
        return participant_group_relationship.data_value_set.filter(
            parameter=get_activity_performed_parameter(),
            int_value=activity.pk,
            round_data=round_data).exists()

    def is_available_now(self, activity):
        if activity.available_all_day:
            return True
        current_time = datetime.now().time()
        availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
        return availabilities.exists()

    def is_activity_available(self, activity, participant_group_relationship, round_data):
        round_configuration = round_data.round_configuration
        experiment_configuration = round_configuration.experiment_configuration
        unlocked_activities = []
        treatment_type = get_treatment_type(experiment_configuration=experiment_configuration).string_value
        if is_scheduled_activity_experiment(treatment_type=treatment_type):
            # find scheduled set of activities
            unlocked_activities = self.scheduled(round_configuration)
        else:
            # otherwise, unlocked activities are based on the group's level
            unlocked_activities = Activity.objects.unlocked(
                level=get_footprint_level(participant_group_relationship.group, round_data))
        if activity in unlocked_activities:
            # check for time availability. high school treatment doesn't have
            # time requirements however.
            if is_high_school_treatment(treatment_type=treatment_type) or self.is_available_now(activity):
                # if it is currently available, make sure they haven't already performed it
                already_performed = self.already_performed(activity, participant_group_relationship, round_data)
                return not already_performed
        return False

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
    group_activity = models.BooleanField(
        default=False,
        help_text=_('''Activity with shared group effect multipliers, e.g., ride sharing'''))
    # currently unused
    cooldown = models.PositiveIntegerField(
        default=1, null=True, blank=True,
        help_text=_('''How much time must elapse before this activity becomes available again, in 1h intervals'''))
    icon = models.ImageField(upload_to='lighterprints/activity-icons/')
    # for user submitted activities
    creator = models.ForeignKey(User, null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = models.DateTimeField(default=datetime.now)
    # for the "in-the-wild" app, activities unlock other sets of activities in
    # a tree-like fashion
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children_set')
    is_public = models.BooleanField(default=False)

    objects = ActivityManager.from_queryset(ActivityQuerySet)()
    data_fields = [name, display_name, points]
    _default_attrs = ('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day',
                      'level', 'icon_url', 'icon_name', 'personal_benefits', 'points', 'time_slots')

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

    def to_dict(self):
        ck = 'activity.%s' % self.pk
        cv = cache.get(ck)
        if cv is None:
            cv = {}
            for attr_name in self._default_attrs:
                cv[attr_name] = getattr(self, attr_name, None)
            cache.set(ck, cv)
        return cv

    def __str__(self):
        return '{} : {}'.format(self.label, self.points)

    class MPTTMeta:
        level_attr = 'mptt_level'

    class Meta:
        ordering = ['level', 'name']


def _to_hour(dt):
    return dt.strftime('%I%p').lstrip('0').lower()


class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return '%s (%s - %s)' % (self.activity, self.start_time, self.end_time)

    @property
    def time_slot(self):
        return '%s-%s' % (_to_hour(self.start_time), _to_hour(self.end_time))

    def to_dict(self, attrs=('start_time', 'end_time')):
        d = {}
        for attr_name in attrs:
            d[attr_name] = getattr(self, attr_name, None)
        return d

    class Meta:
        ordering = ['activity', 'start_time']


@simplecache
def get_linear_public_good_parameter():
    return Parameter.objects.for_experiment(name='lfp_linear_public_good')


@simplecache
def get_leaderboard_parameter():
    return Parameter.objects.for_experiment(name='leaderboard')


@simplecache
def get_available_activity_parameter():
    return Parameter.objects.for_round(name='available_activity')


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
    return Parameter.objects.get(name='lfp_treatment_type')


def is_linear_public_good_experiment(experiment_configuration, default=False):
    """
    linear public good experiment: earnings depend on group average points, e.g., group average points * $.02
    """
    return experiment_configuration.get_parameter_value(parameter=get_linear_public_good_parameter(),
                                                        default=default).boolean_value


def has_leaderboard(experiment_configuration, default=False):
    return experiment_configuration.get_parameter_value(parameter=get_leaderboard_parameter(),
                                                        default=default).boolean_value


def get_group_threshold(experiment_configuration, default=125):
    if is_linear_public_good_experiment(experiment_configuration):
        return 250
    else:
        return 125


def get_footprint_level_dv(group, round_data=None):
    if round_data is None:
        round_data = group.current_round_data
    return GroupRoundDataValue.objects.get(group=group, round_data=round_data,
                                           parameter=get_footprint_level_parameter())


def get_footprint_level(group, round_data=None, **kwargs):
    return get_footprint_level_dv(group, round_data=round_data, **kwargs).int_value


def get_experiment_completed_dv(group, round_data=None):
    return group.get_data_value(parameter=get_experiment_completed_parameter(), round_data=round_data)


def get_treatment_type(experiment=None, experiment_configuration=None, default_treatment_type='SCHEDULED_ACTIVITY',
                       **kwargs):
    """
    possible treatment types:
    SCHEDULED_ACTIVITY / HIGH_SCHOOL / LEVEL_BASED / COMMUNITY
    """
    if experiment_configuration is None:
        experiment_configuration = experiment.experiment_configuration
    treatment_type = experiment_configuration.get_parameter_value(parameter=get_treatment_type_parameter(),
                                                                  default=default_treatment_type)
    return treatment_type
