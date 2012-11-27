from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from functools import partial
from model_utils.managers import PassThroughManager
from vcweb.core import signals, simplecache, enum
from vcweb.core.models import (Experiment, ExperimentMetadata, GroupRoundDataValue, ParticipantGroupRelationship, ParticipantRoundDataValue, Parameter, User)
from vcweb.core.services import fetch_foursquare_categories
import collections
from datetime import datetime, date, time, timedelta
from mptt.models import MPTTModel, TreeForeignKey, TreeManager
from brabeion import badges
from brabeion.base import Badge, BadgeAwarded
from lxml import etree

import logging
logger = logging.getLogger(__name__)

# signal handlers for midnight tick + round_started
@receiver(signals.participant_added)
def new_participant(sender, experiment=None, participant_group_relationship=None, **kwargs):
    if experiment.is_public and experiment.experiment_metadata == get_lighterprints_experiment_metadata():
        logger.debug("new participant %s for public experiment %s", participant_group_relationship, experiment)
        if participant_group_relationship is not None:
            get_unlocked_activities(participant_group_relationship)

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, **kwargs):
    logger.debug("updating active experiments")
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.group_set.all():
            footprint_level_grdv = get_footprint_level_dv(group)
            if should_advance_level(group, footprint_level_grdv.value):
                # advance group level
                footprint_level_grdv.value = min(footprint_level_grdv.value + 1, 3)
                footprint_level_grdv.save()

@receiver(signals.round_started)
def round_started_handler(sender, experiment=None, **kwargs):
    if sender != get_lighterprints_experiment_metadata().pk:
        return
    # FIXME: See if we can push this logic up to core..
    current_round_data = experiment.current_round_data
    footprint_level_parameter = get_footprint_level_parameter()
    participant_level_parameter = get_participant_level_parameter()
# only create the footprint level parameter, the participant activity performed data values will be created each time.
    for group in experiment.group_set.all():
        current_round_data.group_data_value_set.create(group=group, parameter=footprint_level_parameter, int_value=1)
        for pgr in group.participant_group_relationship_set.all():
            # create participant level data value for each participant
            ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr, parameter=participant_level_parameter, int_value=1)
            # create initial unlocked set of data values
            get_unlocked_activities(pgr)


ActivityStatus = enum('AVAILABLE', 'COMPLETED', 'UNAVAILABLE')

class ActivityBadge(Badge):
    slug = "activity"
    levels = ["Bronze", "Silver", "Gold"]
    events = [ "activity_performed", ]
    multiple = False
    def award(self, **state):
        user = state["user"]
        activity = state["activity"]
        participant_group_relationship = ParticipantGroupRelationship.objects.get(group__experiment=get_lighterprints_public_experiment(),
                participant=user.participant)
        number_of_times_performed = participant_group_relationship.participant_data_value_set.filter(
                parameter=get_activity_performed_parameter()).count()
        if number_of_times_performed < 3:
            return None
        elif number_of_times_performed == 3:
            level = 1
        elif number_of_times_performed == 8:
            level = 2
        elif number_of_times_performed == 15:
            level = 3
        return BadgeAwarded(level=level, slug=activity.name, name=activity.name, description=activity.description)

badges.register(ActivityBadge)

class GreenButtonIntervalBlock(models.Model):
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='gb_interval_block_set')
    date_created = models.DateTimeField(default=datetime.now)
    date = models.DateTimeField()
    start = models.PositiveIntegerField(_('Seconds from epoch from GB data'))
    total_duration = models.PositiveIntegerField(_('Total duration for this interval block'))

class GreenButtonIntervalReading(models.Model):
    interval_block = models.ForeignKey(GreenButtonIntervalBlock, related_name='interval_reading_set')
    date_created = models.DateTimeField(default=datetime.now)
    date = models.DateTimeField()
    seconds_from_epoch = models.PositiveIntegerField(_('Number of seconds from epoch from GB data, should be the same as date'))
    watt_hours = models.PositiveIntegerField(_('Energy meter reading in watt-hours'))
    millicents = models.PositiveIntegerField(_('total millicents cost for this interval'), null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

class GreenButtonParser(object):
    xmlns = { 'gb': 'http://naesb.org/espi' }

    def __init__(self, xmltree=None, fh=None, **kwargs):
        if xmltree is not None:
            self.xmltree = xmltree
        elif fh is not None:
            fh.seek(0)
            self.xmltree = etree.parse(fh)
        else:
            logger.warning("parser initialized without valid xmltree, make sure you set it before using any methods.")

    def find(self, expr, node=None, **kwargs):
        if node is None:
            node = self.xmltree
        return node.find(expr, namespaces=self.xmlns)

    def findall(self, expr, node=None, **kwargs):
        if node is None:
            node = self.xmltree
        return node.findall(expr, namespaces=self.xmlns)

    def interval_block(self):
        return self.find('//gb:IntervalBlock')

    def interval_readings(self, node=None):
        return self.findall('gb:IntervalReading', node)

    def interval_data(self, node=None):
        return self.find('gb:interval', node)

    def extract(self, node, exprs=None, converter=int):
        ''' returns a dict of expr -> value for each expr '''
        return collections.defaultdict(lambda: None, [(expr, converter(self.find('gb:%s' % expr, node).text)) for expr in exprs])

    def get_interval_data(self, node=None):
        interval_data = self.interval_data(node)
        return self.extract(interval_data, exprs=['duration', 'start'])

    def get_interval_reading_data(self, interval_reading_node):
        time_period = self.find('gb:timePeriod', interval_reading_node)
        data = self.extract(time_period, exprs=['duration', 'start'])
        data.update(self.extract(interval_reading_node, exprs=['value', 'cost']))
        return data

    def create_interval_block(self, participant_group_relationship):
        interval_block = self.interval_block()
        interval_data = self.get_interval_data(interval_block)
        start = interval_data['start']
        total_duration = interval_data['duration']
        existing_interval_blocks = GreenButtonIntervalBlock.objects.filter(start=start)
        if existing_interval_blocks.count() > 0:
            logger.warning("green button data already exists, deleting existing set: %s", existing_interval_blocks)
            existing_interval_blocks.delete()
        gb_interval_block = GreenButtonIntervalBlock.objects.create(date=datetime.fromtimestamp(start), start=start,
                total_duration=total_duration, participant_group_relationship=participant_group_relationship)
        return interval_block, gb_interval_block

    def create_interval_reading(self, interval_reading_node, gb_interval_block):
        data = self.get_interval_reading_data(interval_reading_node)
        start = data['start']
        gb_interval_reading = gb_interval_block.interval_reading_set.create(
                date=datetime.fromtimestamp(start),
                seconds_from_epoch=start,
                watt_hours=data['value'],
                millicents=data['cost'])
        return interval_reading_node, gb_interval_reading

    def create_models(self, participant_group_relationship):
        interval_block_node, gb_interval_block = self.create_interval_block(participant_group_relationship)
        models = [gb_interval_block]
        for interval_reading_node in self.interval_readings(interval_block_node):
            gb_interval_reading = self.create_interval_reading(interval_reading_node, gb_interval_block)
            models.append(gb_interval_reading)
        return models

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

class ActivityManager(TreeManager, PassThroughManager):
    def currently_available(self, level=1, **kwargs):
        current_time = datetime.now().time()
        available_time_slot = dict(start_time__lte=current_time, end_time__gte=current_time)
# find all activities with time slots that fall within current time
        activities = [activity_availability.activity for activity_availability in ActivityAvailability.objects.select_related(depth=1).filter(models.Q(**available_time_slot))]
# add activities that are available all day
        activities.extend(Activity.objects.filter(available_all_day=True))
# only include activities that are at this level
        return filter(lambda a: a.level == level, activities)

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
    creator = models.ForeignKey(User, null=True)
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
        if self.available_all_day:
            return 'available all day'
        else:
            return ','.join([availability.time_slot for availability in self.availability_set.all()])

    def to_dict(self, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'icon_url', 'personal_benefits', 'points', 'time_slots')):
        activity_as_dict = {}
        for attr_name in attrs:
            activity_as_dict[attr_name] = getattr(self, attr_name, None)
        return activity_as_dict

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.points)

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
def get_foursquare_category_ids(parent_category_name='Travel', subcategory_names=['Light Rail', 'Bike', 'Bus Station', 'Train Station']):
    categories = fetch_foursquare_categories()
    for parent_category in categories:
        if parent_category_name in parent_category['name']:
            return [subcategory['id'] for subcategory in parent_category['categories'] if subcategory['shortName'] in subcategory_names]

@simplecache
def get_lighterprints_public_experiment():
    # FIXME: hacky
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            experiment_configuration__is_public=True)[0]

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

@simplecache
def get_participant_level_parameter():
    return Parameter.objects.get(name='participant_level')

@simplecache
def get_activity_unlocked_parameter():
    return Parameter.objects.get(name='activity_unlocked')

@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.get(name='activity_performed')

@simplecache
def get_footprint_level_parameter():
    return Parameter.objects.get(name='footprint_level')

@simplecache
def get_treatment_type_parameter():
    return Parameter.objects.get(name='treatment_type')

def get_footprint_level_dv(group):
    return group.get_data_value(parameter=get_footprint_level_parameter())[1]

def get_footprint_level(group):
    return get_footprint_level_dv(group).value

def get_active_experiments():
    # FIXME: add PassThroughManager to ExperimentManager
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(), status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))

# all activity names:
#[u'adjust-thermostat', u'eat-local-lunch', u'enable-sleep-on-computer', u'recycle-materials', u'share-your-ride',
#u'bike-or-walk', u'computer-off-night', u'no-beef', u'recycle-paper', u'air-dry-clothes', u'cold-water-wash',
#u'eat-green-lunch', u'lights-off', u'vegan-for-a-day']

def _lookup_activities(activity_names):
    return Activity.objects.filter(name__in=activity_names)

_levels_to_unlocked_activities = map (lambda x: partial(_lookup_activities, x), (
    ['recycle-paper', 'share-your-ride', 'enable-sleep-on-computer'],
    ['adjust-thermostat'],
    ['eat-local-lunch'],
    ['cold-water-wash'],
    ['no-beef']
    ))

def get_unlocked_activities_by_level(level=0):
    return _levels_to_unlocked_activities[level]()

_unlocking_activities = {
        'recycle-paper': (3, 'recycle-materials'),
        'share-your-ride': (3, 'bike-or-walk'),
        'enable-sleep-on-computer': (3, 'computer-off-night'),
        'adjust-thermostat': (3, 'lights-off'),
        'eat-local-lunch': (3, 'eat-green-lunch'),
        'cold-water-wash': (1, 'air-dry-clothes'),
        'beef-with-poultry': (3, 'vegan-for-a-day'),
        }

def initial_unlocked_activities():
    return Activity.objects.filter(name__in=('recycle-paper', 'share-your-ride', 'enable-sleep-on-computer'))

def create_activity_unlocked_data_values(participant_group_relationship, activity_ids=None):
    if activity_ids is None:
        return None
    logger.debug("unlocking activities: %s", activity_ids)
    dvs = []
    for activity_id in activity_ids:
        unlocked_activity_dv = ParticipantRoundDataValue.objects.create(parameter=get_activity_unlocked_parameter(),
                participant_group_relationship=participant_group_relationship)
        unlocked_activity_dv.value = activity_id
        unlocked_activity_dv.save()
        dvs.append(unlocked_activity_dv)
    return dvs

def get_unlocked_activities(participant_group_relationship):
    # first check if they've performed any activities
    pdvs = participant_group_relationship.participant_data_value_set
    performed_activities = pdvs.filter(parameter=get_activity_performed_parameter())
    unlocked_activities = pdvs.filter(parameter=get_activity_unlocked_parameter())
# FIXME: degenerate data check, remove if unnecessary
    if performed_activities.count() == 0 and unlocked_activities.count() == 0:
        # check if they have any unlocked activities now
        initial_unlocked_activity_ids = initial_unlocked_activities().values_list('id', flat=True)
        # unlock the base set of activities for them
        unlocked_activities = create_activity_unlocked_data_values(participant_group_relationship, initial_unlocked_activity_ids)
    #logger.debug("participant %s performed activities %s\nunlocked: %s", participant_group_relationship, performed_activities, unlocked_activities)
    return unlocked_activities


# returns a tuple of a (list of activity objects converted to dicts and an activity_by_level list of lists (level -> list of activity
# objects converted to dicts).
def get_all_activities_tuple(participant_group_relationship, activities=None):
    if activities is None:
        activities = Activity.objects.all()
    activity_dict_list = []
    level_activity_list = []
    available_activities = get_available_activities(participant_group_relationship)
    available_activity_ids = [activity.pk for activity in available_activities]

    for activity in activities:
        activity_dict = activity.to_dict()
        try:
            activity_dict['availabilities'] = [availability.to_dict() for availability in ActivityAvailability.objects.filter(activity=activity)]
            activity_dict['available_now'] = activity.pk in available_activity_ids
        except Exception as e:
            logger.debug("failed to get authenticated activity list: %s", e)
        activity_dict_list.append(activity_dict)
        level = activity.level
        # XXX: assumes activity list is ordered by level
        if level > len(level_activity_list):
            level_activity_list.append([])
        level_activity_list[level-1].append(activity_dict)
    return (activity_dict_list, level_activity_list)

def get_available_activities(participant_group_relationship=None, ignore_time=False):
    if participant_group_relationship is None:
        logger.warn("asking for available activities with no participant, returning all activities")
        return Activity.objects.all()
    else:
        logger.debug("requesting available activities for pgr %s (%d)", participant_group_relationship, participant_group_relationship.pk)
        # FIXME: push this logic into the manager / queryset?
        group_level = get_footprint_level(participant_group_relationship.group)
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
        logger.debug("performed activity ids: %s", performed_activity_ids)
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
    level = get_footprint_level(participant_group_relationship.group)
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


def average_points_per_person(group):
    return get_group_score(group)[0]

# returns a tuple of the average points per person and the total points for
# the given group
def get_group_score(group, start=None, end=None):
    # establish date range
    # grab all of yesterday's participant data values, starting at 00:00:00 (midnight)
    total_points = 0
    activities_performed_qs = group.get_participant_data_values(parameter=get_activity_performed_parameter())
    if not group.experiment.is_public:
        if start is None or end is None:
            start = date.today()
            end = start + timedelta(1)
        activities_performed_qs = activities_performed_qs.filter(date_created__range=(start, end))
    for activity_performed_dv in activities_performed_qs:
        activity = activity_performed_dv.value
        total_points += activity.points
    average = total_points / group.size
    logger.debug("total carbon savings: %s divided by %s members = %s per person", total_points, group.size, average)
    return (average, total_points)

def points_to_next_level(current_level):
    ''' returns the number of average points needed to advance to the next level '''
    if current_level == 1:
        return 50
    elif current_level == 2:
        return 125
    elif current_level == 3:
        return 225

def should_advance_level(group, level, max_level=3):
    if level < max_level:
        return average_points_per_person(group) >= points_to_next_level(level)
    return False

def get_activity_performed_counts(participant_group_relationship, activity_performed_parameter=None):
    if activity_performed_parameter is None:
        activity_performed_parameter = get_activity_performed_parameter()
    return participant_group_relationship.participant_data_value_set.filter(parameter=activity_performed_parameter).values('int_value').order_by().annotate(count=models.Count('int_value'))
