from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.aggregates import Max
from string import Template
from vcweb.core import signals
import base64
from  datetime import datetime
import hashlib
import logging
import random
import re
import simplejson

logger = logging.getLogger(__name__)


"""
Contains all data models used in the core as well as a number of helper functions.

Is getting monolithically unwieldy.  Consider splitting into models
subdirectory

tick handlers.
handles each second tick.  Might rethink this and use timed / delayed tasks in celery execute at the end of each round for
controlled experiments and for longer-scale experiments use 1 minute granularity for performance sake.
"""
def second_tick_handler(sender, time=None, **kwargs):
    logger.debug("handling second tick signal at %s" % time)
    logger.debug("kwargs: %s" % kwargs)
    # inspect all active experiments and update their time left
    Experiment.objects.increment_elapsed_time(status='ROUND_IN_PROGRESS')

signals.second_tick.connect(second_tick_handler, sender=None)

class ExperimentMetadataManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(namespace=key)

"""
ExperimentMetadata contains records for each type of supported and implement
experiment.  A single app could add multiple experiment metadata records but
they should be closely related.
"""
class ExperimentMetadata(models.Model):
    title = models.CharField(max_length=255)
    # the URL fragment that this experiment_metadata will occupy,
    namespace_regex = re.compile(r'^(?:[/]?[a-z0-9_]+\/?)+$')
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=namespace_regex)])
    # short name slug
    short_name = models.SlugField(max_length=32, unique=True, null=True)
    description = models.TextField(null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    about_url = models.URLField(null=True, blank=True, verify_exists=True)
    logo_url = models.URLField(null=True, blank=True, verify_exists=True)
    default_configuration = models.ForeignKey('ExperimentConfiguration', null=True, blank=True)

    objects = ExperimentMetadataManager()

    def natural_key(self):
        return [self.namespace]

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.namespace)

    class Meta:
        ordering = ['namespace', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, verify_exists=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u"%s (%s)" % (self.name, self.url)

class CommonsUser(models.Model):
    """
    for docs on related_name see
        http://docs.djangoproject.com/en/dev/topics/db/models/#be-careful-with-related-name
    this related name makes user.experimenter and user.participant resolvable.
    FIXME: should revisit to see if this is recommended practice.
    (either one or the other)
    """
    user = models.OneToOneField(User, related_name='%(class)s', verbose_name=u'Django User', unique=True)
    failed_password_attempts = models.PositiveIntegerField(default=0)
    institution = models.ForeignKey(Institution, null=True, blank=True)

    @property
    def full_name(self):
        return self.user.get_full_name()

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def email(self):
        return self.user.email

    def is_authenticated(self):
        return self.user.is_authenticated()

    def __unicode__(self):
        return u"%s (%s)" % (self.user.get_full_name(), self.user.email)

    class Meta:
        abstract = True


class Experimenter(CommonsUser):
    approved = models.BooleanField(default=False)
    class Meta:
        ordering = ['user']

class ExperimentConfiguration(models.Model):
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='configurations')
    creator = models.ForeignKey(Experimenter, related_name='experiment_configurations')
    name = models.CharField(max_length=255)
    max_number_of_participants = models.PositiveIntegerField(default=0)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    max_group_size = models.PositiveIntegerField(default=5)

    @property
    def final_sequence_number(self):
        return self.round_configurations.count()

    @property
    def last_round_sequence_number(self):
        return self.round_configurations.aggregate(sequence_number=Max('sequence_number'))['sequence_number']

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    def __unicode__(self):
        return u"ExperimentConfiguration %s for %s" % (self.name, self.experiment_metadata)

    class Meta:
        ordering = ['experiment_metadata', 'creator', 'date_created']


class ExperimentManager(models.Manager):
    def get_all_active(self):
        return self.filter(status='ACTIVE')

    def increment_elapsed_time(self, status='ROUND_IN_PROGRESS'):
        if status:
            es = self.filter(status=status)
            es.update(current_round_elapsed_time=models.F('current_round_elapsed_time') + 1,
                    total_elapsed_time=models.F('total_elapsed_time') + 1)
            # check each experiment's total_elapsed_time against the total allotted time and
            # issue round_stopped signals to experiments that need to be stopped.
            for experiment in es.all():
                experiment.check_elapsed_time()

# an actual instance of an experiment; represents a concrete
# parameterization of this experiment.
class Experiment(models.Model):
    STATUS_CHOICES = (('INACTIVE', 'Not active'),
                      ('ACTIVE', 'Active, no round in progress'),
                      ('PAUSED', 'Paused'),
                      ('ROUND_IN_PROGRESS', 'Round in progress'),
                      ('COMPLETED', 'Completed'))
    (INACTIVE, ACTIVE, PAUSED, ROUND_IN_PROGRESS, COMPLETED) = [ choice[0] for choice in STATUS_CHOICES ]
    authentication_code = models.CharField(max_length=32, default="vcweb.auth.code")
    current_round_sequence_number = models.PositiveIntegerField(default=0)
    experimenter = models.ForeignKey(Experimenter, related_name='experiments')
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    experiment_configuration = models.ForeignKey(ExperimentConfiguration,
                                                 related_name='experiments')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default='INACTIVE')
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    start_date_time = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format
    # 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32, null=True, blank=True)
    """ how often the experiment_metadata server should tick. """
    tick_duration = models.CharField(max_length=32, null=True, blank=True)

    """
    total elapsed time in seconds since this experiment_metadata was
    started, incremented by the heartbeat monitor.
    """
    total_elapsed_time = models.PositiveIntegerField(default=0)
    """ current round start time """
    current_round_start_time = models.DateTimeField(null=True, blank=True)
    """ elapsed time in seconds for the current round. """
    current_round_elapsed_time = models.PositiveIntegerField(default=0)
    """
    Experimenter driven experiments have checkpoints where the experimenter
    needs to explicitly signal the system to move to the next round or stage.
    """
    is_experimenter_driven = models.BooleanField(default=True)
    """ name of the AMQP exchange hosting this experiment """
    amqp_exchange_name = models.CharField(max_length=64, default="vcweb.default.exchange")

    '''
    short slug to use instead of pk
    FIXME: still needs to be implemented
    '''
    slug = models.SlugField(max_length=16, unique=True, null=True)

    objects = ExperimentManager()

    @property
    def is_time_expired(self):
        return self.current_round_elapsed_time >= self.current_round.duration

    @property
    def is_round_in_progress(self):
        return self.status == 'ROUND_IN_PROGRESS'

    @property
    def is_data_round_in_progress(self):
        return self.is_round_in_progress and self.current_round.has_data_parameters

    @property
    def time_remaining(self):
        return self.current_round.duration - self.current_round_elapsed_time

    @property
    def is_timed_round(self):
        return self.current_round.duration > 0

    @property
    def channel_name(self):
        return "%s.%s" % (self.namespace, self.pk)

    @property
    def participant_url(self):
        return "/%s/participate" % self.get_absolute_url()

    @property
    def management_url(self):
        return "/%s/experimenter" % self.get_absolute_url()

    @property
    def stop_url(self):
        return "%s/stop" % self.controller_url

    @property
    def monitor_url(self):
        return "%s/monitor" % self.controller_url

    @property
    def round_status_display(self):
        return "Round %s of %s, %s" % (self.current_round.sequence_number, self.experiment_configuration.final_sequence_number, self.get_status_display())

    @property
    def status_line(self):
        return "%s: id %s, status: %s, round %s of %s" % (
                self.experiment_metadata.title,
                self.pk,
                self.get_status_display(),
                self.current_round.sequence_number,
                self.experiment_configuration.final_sequence_number)

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    @property
    def controller_url(self):
        return "/experiment/%s" % self.pk

    def get_absolute_url(self):
        return "%s/%s" % (self.experiment_metadata.namespace, self.pk)

    @property
    def current_round_template(self):
        return self.current_round.template_path

    @property
    def current_round(self):
        return self.get_round_configuration(self.current_round_sequence_number)

    @property
    def current_round_data(self):
        round_data, created = self.round_data.get_or_create(round_configuration=self.current_round)
        return round_data

    @property
    def next_round(self):
       if self.has_next_round:
          return self.get_round_configuration(self.current_round_sequence_number + 1)
       else:
          return self.current_round

    @property
    def previous_round(self):
        return self.get_round_configuration(max(self.current_round_sequence_number - 1, 0))

    @property
    def has_next_round(self):
        return self.current_round_sequence_number < self.experiment_configuration.final_sequence_number

    @property
    def is_last_round(self):
        return self.current_round_sequence_number == self.experiment_configuration.final_sequence_number

    @property
    def is_active(self):
        return self.status != 'INACTIVE'

    def parameters(self, scope=None):
        ps = self.experiment_metadata.parameters
        return ps.filter(scope=scope) if scope else ps

    def activate(self):
        if not self.is_active:
            self.allocate_groups()
            self.status = 'ACTIVE'
            self.save()
        return self

    def allocate_groups(self, randomize=True):
        # clear out all existing groups
        # FIXME: record previous mappings in activity log.
        self.groups.all().delete()
        # seed the initial group.
        current_group = self.groups.create(number=1, max_size=self.experiment_configuration.max_group_size)
        current_group.initialize_data_parameters()
        participants = list(self.participants.all())
        if randomize:
            random.shuffle(participants)

        for p in participants:
            if current_group.is_full:
                current_group = current_group.create_next_group()
                current_group.initialize_data_parameters()
            current_group.add_participant(p)

        # XXX: if there a performance hit here, should probably do a void return instead
        # or collect the groups as they are added
        return self.groups

    def get_round_configuration(self, sequence_number):
        return self.experiment_configuration.round_configurations.get(sequence_number=sequence_number)

    def get_template_path(self, name):
        return "%s/%s" % (self.namespace, name)

    def advance_to_next_round(self):
        if self.is_round_in_progress:
            self.end_round()
        if self.has_next_round:
            self.current_round_elapsed_time = 0
            self.current_round_sequence_number += 1
            self.save()
            # initialize group parameters if necessary
            for g in self.groups.all():
                g.initialize_data_parameters()
        else:
            logger.warning("trying to advance past the last round - no-op")

    def start_round(self, sender=None):
        self.status = 'ROUND_IN_PROGRESS'
        ''' get_or_create round_data for this round '''
        self.current_round_data
        self.current_round_elapsed_time = 0
        self.current_round_start_time = datetime.now()
        self.save()
        self.activity_log.create(log_message='Starting round.', round_configuration=self.current_round)
        # FIXME: would prefer using self.namespace as a default but django's
        # managed unicode strings don't work as senders
        sender = self.experiment_metadata.pk if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        # notify registered game handlers
        logger.debug("About to send round started signal with sender %s" % sender)
        return signals.round_started.send(sender, experiment=self, time=datetime.now(), round_configuration=self.current_round)

    def end_round(self, sender=None):
        self.status = 'ACTIVE'
        self.current_round_elapsed_time = max(self.current_round_elapsed_time, self.current_round.duration)
        self.save()
        self.activity_log.create(log_message='Ending round with elapsed time %s.' % self.current_round_elapsed_time, round_configuration=self.current_round)
        sender = self.experiment_metadata.pk if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        logger.debug("about to send round ended signal with sender %s" % sender)
        return signals.round_ended.send(sender, experiment=self, round_configuration=self.current_round)

    def stop(self):
        self.status = 'INACTIVE'
        self.save()

    def check_elapsed_time(self):
        if self.is_timed_round and self.is_time_expired:
            self.end_round()

    def to_json(self, *args):
        return simplejson.dumps({
            'experiment': {
                'pk': self.pk,
                'is_active': self.is_active,
                'is_round_in_progress': self.is_round_in_progress,
                },
            })

    """ returns a fresh copy of this experiment with configuration / metadata intact """
    def clone(self, experimenter=None):
        if not experimenter:
            experimenter = self.experimenter
        return Experiment.objects.create(experimenter=experimenter,
                          authentication_code=self.authentication_code,
                          experiment_metadata=self.experiment_metadata,
                          experiment_configuration=self.experiment_configuration,
                          duration=self.duration,
                          tick_duration=self.tick_duration,
                          is_experimenter_driven=self.is_experimenter_driven,
                          status=Experiment.INACTIVE
                          )


    def __unicode__(self):
        return u"%s | #%s" % (self.experiment_metadata.title, self.pk)

    def ___eq___(self, other):
        return self.pk == other.pk

    def ___cmp___(self, other):
        return self.pk.___cmp___(other.pk)

    def ___hash___(self):
        return self.pk.___hash___()

class RoundConfiguration(models.Model):
# maps round type name to (description, default_template_name)
    ROUND_TYPES_DICT = dict(REGULAR=('Regular interactive experiment round', 'participate.html'),
            CHAT=('Chat round', 'chat.html'),
            DEBRIEFING=('Debriefing round', 'debriefing.html'),
            INSTRUCTIONS=('Instructions round', 'instructions.html'),
            PRACTICE=('Practice round', 'practice.html'),
            QUIZ=('Quiz round', 'quiz.html'))
    ROUND_TYPES = (CHAT, DEBRIEFING, INSTRUCTIONS, PRACTICE, QUIZ, REGULAR) = sorted(ROUND_TYPES_DICT.keys())

    ROUND_TYPE_CHOICES = [(round_type, ROUND_TYPES_DICT[round_type][0]) for round_type in ROUND_TYPES]

    experiment_configuration = models.ForeignKey(ExperimentConfiguration,
                                                 related_name='round_configurations')
    sequence_number = models.PositiveIntegerField(help_text='Used internally to determine the ordering of the rounds in an experiment in ascending order, e.g., 1,2,3,4,5')
    display_number = models.PositiveIntegerField(default=0,
                                               help_text='The round number to be displayed with this round.  If set to zero, defaults to the internally used sequence_number.')
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    """
    How long should this round execute before advancing to the next?
    Interpreted as whole seconds.
    """
    duration = models.PositiveIntegerField(default=0,
                                           help_text='Duration in seconds.  0 means an untimed round that can only be advanced by an experimenter.')
    """ instructions, if any, to display before the round begins """
    instructions = models.TextField(null=True, blank=True)
    """ debriefing, if any, to display after the round ends """
    debriefing = models.TextField(null=True, blank=True)
    round_type = models.CharField(max_length=32,
                                  choices=ROUND_TYPE_CHOICES,
                                  default=REGULAR)
    """
    name of a custom template to be used this round.  e.g., if set to
    quiz_2.html in the forestry experiment app, this would be loaded from
    forestry/templates/forestry/quiz_2.html
    """
    template_name = models.CharField(max_length=64, null=True, blank=True,
                                            help_text='''The name of the template to use to render when executing this round.
                                            This file should exist in your templates directory as your-experiment-namespace/template-name.html,
                                            e.g., if set to foo.html, vcweb will look for templates/forestry/foo.html''')

    @property
    def custom_template_name(self):
        return self.template_name if self.template_name else self.default_template_name

    @property
    def default_template_name(self):
        return RoundConfiguration.ROUND_TYPES_DICT[self.round_type][1]

    @property
    def template_path(self):
        return "%s/%s" % (self.experiment_configuration.namespace, self.custom_template_name)

    @property
    def round_number(self):
        return self.sequence_number if self.display_number == 0 else self.display_number

    @property
    def is_debriefing_round(self):
        return self.round_type == RoundConfiguration.DEBRIEFING

    @property
    def is_chat_round(self):
        return self.round_type == RoundConfiguration.CHAT

    @property
    def is_instructions_round(self):
        return self.round_type == RoundConfiguration.INSTRUCTIONS

    @property
    def is_quiz_round(self):
        return self.round_type == RoundConfiguration.QUIZ

    @property
    def is_practice_round(self):
        return self.round_type == RoundConfiguration.PRACTICE

    @property
    def is_regular_round(self):
        return self.round_type == RoundConfiguration.REGULAR

    @property
    def has_data_parameters(self):
        return self.round_type in (RoundConfiguration.PRACTICE, RoundConfiguration.REGULAR)

    def get_parameter(self, name):
        parameter = Parameter.objects.get(name=name, scope=Parameter.ROUND_SCOPE)
        round_parameter, created = self.round_parameter_values.get_or_create(parameter=parameter)
        if created:
            logger.debug("created new parameter %s for %s" % (parameter, self))
        return round_parameter

    def set_parameter(self, name=None, value=None):
        parameter = Parameter.objects.get(name=name, scope=Parameter.ROUND_SCOPE)
        parameter_value, created = self.round_parameter_values.get_or_create(parameter=parameter)
        parameter_value.value = value
        parameter_value.save()

    def get_parameter_value(self, name):
        return self.round_parameter_values.get(parameter__name=name).value

    def get_debriefing(self, participant_id=None, **kwargs):
        return self.templatize(self.debriefing, participant_id, kwargs)

    def get_instructions(self, participant_id=None, **kwargs):
        return self.templatize(self.instructions, participant_id, kwargs)


    def templatize(self, template_string, participant_id=None, **kwargs):
        return Template(template_string).substitute(kwargs, round_number=self.display_number, participant_id=participant_id)

    def __unicode__(self):
        return u"Round %d, sequence: %d" % (self.round_number, self.sequence_number)

    @property
    def display_label(self):
        if self.is_regular_round:
            return u"Round %d" % self.round_number
        return u"%s (%s)" % (self.get_round_type_display(), self.round_number)

    class Meta:
        ordering = [ 'experiment_configuration', 'sequence_number', 'date_created' ]


class ParameterManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(name=key)

class Parameter(models.Model):
    PARAMETER_TYPES = (('int', 'Integer value'),
                       ('string', 'String value'),
                       ('float', 'Float value'),
                       ('boolean', (('True', True), ('False', False))),
                       ('enum', 'Enumeration'))

    NONE_VALUES_DICT = dict(map(lambda x,y: (x[0], y), PARAMETER_TYPES, [0, '', 0.0, False, None]))
    #dict(zip([parameter_type[0] for parameter_type in PARAMETER_TYPES], [0, '', 0.0, False, None]))

    '''
    all converters are one-arg functions that convert string input into
    the appropriate data type.
    NOTE: they expect already validated string data and will throw ValueErrors
    on invalid input.
    '''
    CONVERTERS = {
            'int': int,
            'string':str,
            'float': float,
            'boolean': lambda x: bool(x) and str(x).lower() != 'false'
            }

    GROUP_SCOPE = 'group'
    PARTICIPANT_SCOPE = 'participant'
    ROUND_SCOPE = 'round'
    EXPERIMENT_SCOPE = 'experiment'

    SCOPE_CHOICES = ((ROUND_SCOPE, 'Parameter applies just for this round'),
                     (EXPERIMENT_SCOPE, 'Parameter applies to this entire experiment'),
                     (GROUP_SCOPE, 'Parameter applies to the entire group'),
                     (PARTICIPANT_SCOPE, 'Parameter is for a single participant'))

    scope = models.CharField(max_length=32, choices=SCOPE_CHOICES, default=ROUND_SCOPE)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)
    default_value_string = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(Experimenter)
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='parameters')
    enum_choices = models.TextField(null=True, blank=True)
    is_required = models.BooleanField(default=False)

    objects = ParameterManager()

    @property
    def value_field_name(self):
        return '%s_value' % (self.type)

    @property
    def none_value(self):
        return Parameter.NONE_VALUES_DICT[self.type]

    @property
    def default_value(self):
        return self.convert(self.default_value_string)

    @property
    def label(self):
        if self.display_name:
            return self.display_name
        return self.name.replace('_', ' ').title()

    def is_integer_type(self):
        return self.type == 'int'

    def is_boolean_type(self):
        return self.type == 'boolean'

    def is_float_type(self):
        return self.type == 'float'

    def is_string_type(self):
        return self.type == 'string'

    def convert(self, value=None):
        converter = Parameter.CONVERTERS[self.type]
        try:
            return converter(value) if converter else value
        except ValueError:
            if self.is_integer_type():
                # last-ditch effort, try converting to float first
                return int(float(value))
            # FIXME: add more checks for other type conversion failures
            pass
        return value

    def __unicode__(self):
        return u"%s parameter: %s (%s, %s)" % (self.experiment_metadata.namespace, self.name, self.type, self.scope)

    class Meta:
        ordering = ['name']

class ParameterizedValue(models.Model):
    parameter = models.ForeignKey(Parameter)
    string_value = models.CharField(max_length=512, null=True, blank=True)
    int_value = models.IntegerField(null=True)
    float_value = models.FloatField(null=True)
    boolean_value = models.NullBooleanField(null=True)
    time_recorded = models.DateTimeField(auto_now_add=True)

    @property
    def value(self):
        value = getattr(self, self.parameter.value_field_name, self.parameter.none_value)
        return value if value is not None else self.parameter.none_value

    @value.setter
    def value(self, obj):
        converted_value = self.parameter.convert(obj)
        setattr(self, self.parameter.value_field_name, converted_value)

    class Meta:
        abstract = True

"""
Used for specific round configuration data.
"""
class RoundParameterValue(ParameterizedValue):
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_parameter_values')

    def __unicode__(self):
        return u"{0} -> [{1}: {2}]".format(self.round_configuration, self.parameter, self.value)


"""
A DataValue is used by Groups and Participants.  GroupRoundData
"""
class DataValue(ParameterizedValue):
    experiment = models.ForeignKey(Experiment)

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2} for experiment {3}".format(self.parameter, self.value, self.time_recorded, self.experiment)

    class Meta:
        abstract = True

class Group(models.Model):
    number = models.PositiveIntegerField()
    """ how many members can this group hold at a maximum? Should be specified as a ConfigurationParameter somewhere """
    max_size = models.PositiveIntegerField(default=5)
    experiment = models.ForeignKey(Experiment, related_name='groups')

    """ should return a unique chat / event channel to communicate on """
    @property
    def channel(self):
        return u"%s.%d" % (self.experiment.event_channel_name, self.number)

    @property
    def experiment_channel(self):
        return self.experiment.event_channel_name

    @property
    def size(self):
        return self.participants.count()

    @property
    def current_round(self):
        return self.experiment.current_round

    '''
    Initializes data parameters for all groups in this round, as necessary. 
    If this round already has data parameters, is a no-op.
    '''
    def initialize_data_parameters(self):
        if self.current_round.has_data_parameters:
            round_data = self.current_round_data
            if round_data.group_data_values.filter(group=self).count() == 0:
                logger.debug("no group data values for the current round %s, creating new ones." % round_data)
                self.activity_log.create(round_configuration=self.current_round,
                        log_message="Initializing data parameters for group %s in round %s" % (self, round_data))
                for group_data_parameter in self.data_parameters:
                    self.data_values.create(round_data=round_data, parameter=group_data_parameter)


    '''
    Not as efficient as a simple SQL update because we need to do some type
    conversion / processing to put the value into the appropriate field.
    '''
    def set_data_value(self, parameter_name=None, parameter=None, value=None):
        data_value = self.get_data_value(parameter_name=parameter_name, parameter=parameter)
        data_value.value = value
        self.activity_log.create(round_configuration=self.current_round,
                log_message="setting parameter %s = %s" % (parameter, value))
        data_value.save()

    def subtract(self, parameter=None, amount=0):
        self.add(parameter, -amount)

    def add(self, parameter=None, amount=0):
# could be a float or an int..
        update_dict = { parameter.value_field_name : models.F(parameter.value_field_name) + amount }
        self.activity_log.create(round_configuration=self.current_round,
                log_message="adding %s to this group's %s parameter" % (amount, parameter))
        '''
        vs
        GroupRoundDataValue.objects.filter(group_round_data=self.current_round_data, parameter=parameter).update(**update_dict)
        '''
        updated_rows = self.data_values.filter(round_data=self.current_round_data, parameter=parameter).update(**update_dict)
        if updated_rows != 1:
            logger.error("Updated %s rows, should have been only one..." % updated_rows)
        '''
        data_value = self.current_round_data.data_values.get(parameter=parameter)
        data_value.value += amount
        data_value.save()
        '''
    def has_data_parameter(self, **kwargs):
        criteria = self._data_parameter_criteria(**kwargs)
        try:
            self.data_values.get(**criteria)
            return True
        except:
            return False

    def get_scalar_data_value(self, parameter=None, parameter_name=None):
        return self.get_data_value(parameter=parameter, parameter_name=parameter_name).value

    def get_data_value(self, parameter=None, parameter_name=None):
        criteria = self._data_parameter_criteria(parameter=parameter, parameter_name=parameter_name)
        return self.data_values.get_or_create(**criteria)[0]

    def _data_parameter_criteria(self, parameter=None, parameter_name=None):
        return dict([('parameter', parameter) if parameter else ('parameter__name', parameter_name)],
                round_data=self.current_round_data)


    def get_group_data_values(self, name=None, *names):
        round_data = self.current_round_data
        if names:
            if name: names.append(name)
            return self.data_values.filter(round_data=round_data, parameter__name__in=names)
        elif name:
            return self.data_values.get(round_data=round_data, parameter__name=name)
        else:
            logger.warning("Trying to retrieve data value by name with no args")
        return None

    '''
    Transfers the given parameter to the next round.  If parameter isn't set,
    transfer all parameters to the next round.
    FIXME: If this ends up being surprising or isn't desired behavior for
    common use cases, revisit and remove.
    '''
    def transfer_to_next_round(self, parameter=None, value=None, transfer_existing_value=True):
        if self.experiment.is_last_round:
            logger.warning("Trying to transfer parameter %s to next round but this is the last round" % parameter)
            return
        value = self.get_scalar_data_value(parameter=parameter) if transfer_existing_value else value
        if not parameter:
            for p in self.data_parameters:
                self.transfer_parameter(p, value)
        else:
            self.transfer_parameter(parameter, value)

    def transfer_parameter(self, parameter, value):
        next_round_data, created = self.experiment.round_data.get_or_create(round_configuration=self.experiment.next_round)
        logger.debug("next round data: %s (%s)" % (next_round_data, "created" if created else "retrieved"))
        group_data_value, created = next_round_data.group_data_values.get_or_create(group=self, parameter=parameter, defaults={'value': value})
        if not created:
            group_data_value.value = value
            group_data_value.save()
        return group_data_value

    def get_participant_data_value(self, participant, parameter):
        return ParticipantRoundDataValue.objects.get(round_data=self.current_round_data, participant=participant, parameter=parameter)

    def get_participant_data_values(self, parameter_name=None):
        return ParticipantRoundDataValue.objects.filter(round_data=self.current_round_data, participant__in=self.participants.all(), parameter__name=parameter_name)

    @property
    def data_parameters(self):
        return Parameter.objects.filter(experiment_metadata=self.experiment.experiment_metadata, scope=Parameter.GROUP_SCOPE)


    @property
    def current_round_data(self):
        return self.experiment.current_round_data

    @property
    def current_round_data_values(self):
        return self.current_round_data.group_data_values

    @property
    def is_full(self):
        return self.size >= self.max_size

    @property
    def is_open(self):
        return self.size < self.max_size

    def create_next_group(self):
        return Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment)

    """
    Adds the given participant to this group or a new group if this group is is_full.
    Returns the group the participant was added to.
    If participant is invalid, returns this group as a no-op.
    """
    def add_participant(self, participant):
        if not participant:
            logger.warning("Trying to add invalid participant %s to group %s" % (participant, self))
            return self

        ''' add the participant to this group if there is room, otherwise create and add to a fresh group '''
        group = self if self.is_open else self.create_next_group()
        ParticipantGroupRelationship.objects.create(participant=participant,
                group=group,
                round_joined=self.experiment.current_round,
                participant_number=group.size + 1)
        return group

    def __unicode__(self):
        return u"Group #{0}".format(self.number)

    class Meta:
        ordering = ['experiment', 'number']


"""
round-specific data for a given experiment.  Contains related sets to group_data
(GroupRoundDataValue), participant_data (ParticipantRoundDataValue), and chat_messages (ChatMessage)
"""
class RoundData(models.Model):
    experiment = models.ForeignKey(Experiment, related_name='round_data')
    round_configuration = models.ForeignKey(RoundConfiguration)
    elapsed_time = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return u"Data for Round %s (%s)" % (self.round_configuration.sequence_number, self.round_configuration.get_round_type_display())

    class Meta:
        ordering = [ 'round_configuration' ]

class GroupRoundDataValue(DataValue):
    group = models.ForeignKey(Group, related_name='data_values')
    round_data = models.ForeignKey(RoundData, related_name='group_data_values')

    def __init__(self, *args, **kwargs):
        super(GroupRoundDataValue, self).__init__(*args, **kwargs)
        if not hasattr(self, 'experiment'):
            self.experiment = self.round_data.experiment


    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def __unicode__(self):
        return u"data value {0}: {1} (group {2}, round {3})".format(self.parameter, self.value, self.group, self.round_configuration)
    class Meta:
        ordering = [ 'round_data', 'group', 'parameter' ]

class Participant(CommonsUser):
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participants')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participants')
#    authentication_token = models.CharField(max_length=64, null=True, blank=True)

    @property
    def active_experiments(self):
        return self.experiment_relationships.filter(experiment__status=Experiment.ACTIVE)

    @property
    def inactive_experiments(self):
        return self.experiment_relationships.exclude(experiment__status=Experiment.ACTIVE)

    @property
    def completed_experiments(self):
        return self.experiments_with_status(Experiment.COMPLETED)


    def set_data_value(self, experiment=None, parameter=None, value=None):
        if experiment and parameter and value is not None:
            current_round_data = experiment.current_round_data
            # FIXME: can we simplify?
            participant_data_value, created = current_round_data.participant_data_values.get_or_create(parameter=parameter, participant=self)
            participant_data_value.value = value
            participant_data_value.save()
        else:
            logger.warning("Unable to set data value %s on experiment %s for %s" % (value, experiment, parameter))

    def get_participant_experiment_relationship(self, experiment):
        return ParticipantExperimentRelationship.objects.get(participant=self, experiment=experiment)

    def get_participant_number(self, experiment):
        return ParticipantGroupRelationship.objects.get_participant_number(experiment, self)

    def get_participant_group_relationship(self, experiment):
        return ParticipantGroupRelationship.objects.get_participant_group(experiment, self)

    def get_group(self, experiment):
        return ParticipantGroupRelationship.objects.get_group(experiment, self)

    def experiments_with_status(self, status=Experiment.ACTIVE):
        return self.experiment_relationships.filter(experiment__status=status)

    class Meta:
        ordering = ['user']

"""
Many-to-many relationship entity storing a participant and the experiment they are participating in.
"""
class ParticipantExperimentRelationship(models.Model):
    participant = models.ForeignKey(Participant, related_name='experiment_relationships')
    participant_identifier = models.CharField(max_length=32)
    sequential_participant_identifier = models.PositiveIntegerField()
    experiment = models.ForeignKey(Experiment, related_name='participant_relationships')
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User)
    last_completed_round_sequence_number = models.PositiveIntegerField(default=0)

    def __init__(self, *args, **kwargs):
        super(ParticipantExperimentRelationship, self).__init__(*args, **kwargs)
        self.generate_identifier()

    """ generates a unique identifier for the given participant and experiment stored in this relationship """
    def generate_identifier(self):
        """ set participant_identifier if it hasn't been set already.  """
        if not self.participant_identifier:
            sha1 = hashlib.sha1()
            sha1.update("%s%i%s" % (self.participant.user.email, self.experiment.pk, self.date_created))
            self.participant_identifier = base64.urlsafe_b64encode(sha1.digest())
            self.sequential_participant_identifier = ParticipantExperimentRelationship.objects.filter(experiment=self.experiment).count() + 1
        return self.participant_identifier


    def __unicode__(self):
        return u"Experiment {0} - participant {1} (created {2})".format(self.experiment, self.participant, self.date_created)

class ParticipantGroupRelationshipManager(models.Manager):

    def get_group(self, experiment, participant):
        participant_group = self.get_participant_group(experiment, participant)
        return participant_group.group if participant_group else None

    def get_participant_group(self, experiment, participant):
        try:
            return self.get(group__experiment=experiment, participant=participant)
        except ParticipantGroupRelationship.DoesNotExist:
            logger.warning("Participant %s does not belong to a group in %s" % (participant, experiment))
            return None

    def get_participant_number(self, experiment, participant):
        participant_group = self.get_participant_group(experiment, participant)
        return participant_group.participant_number if participant_group else None

"""
Many-to-many relationship entity storing a participant, group, their participant number in that group, the 
round in which they joined the group, and the datetime that they joined the group.
"""
class ParticipantGroupRelationship(models.Model):
    participant_number = models.PositiveIntegerField()
    participant = models.ForeignKey(Participant, related_name='participant_group_relationships')
    group = models.ForeignKey(Group, related_name = 'participant_group_relationships')
    round_joined = models.ForeignKey(RoundConfiguration)
    date_joined = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    objects = ParticipantGroupRelationshipManager()

    def __unicode__(self):
        return u"{0}: {1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['participant_number', 'participant']

class ChatMessageManager(models.Manager):
    def message(self, experiment, message):
        current_round = experiment.current_round
        for participant in experiment.participants.all():
            yield ChatMessage.objects.create(participant_group_relationship=participant.get_participant_group_relationship(experiment),
                    message=message,
                    round_configuration=current_round,
                    experiment=experiment)

class ChatMessage(models.Model):
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='chat_messages')
    message = models.CharField(max_length=512)
    """ if set, this is a targeted message to the other participant in this group.  If null, this is a broadcast message to the entire group """
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True, related_name='targets')
    date_created = models.DateTimeField(auto_now_add=True)
    round_data = models.ForeignKey(RoundData, related_name='chat_messages')

    objects = ChatMessageManager()

    def __unicode__(self):
        """ return this participant's sequence number combined with the message """
        participant_number = self.participant_group_relationship.participant_number
        return u"{0}: {1}".format(participant_number, self.message)

    @property
    def as_html(self):
        return "<a name='{0}'>{1}</a> | {2}".format(self.pk,
                self.date_created.strftime("%H:%S"), 
                self.__unicode__())

    class Meta:
        ordering = ['date_created', 'round_data']

"""
Stores participant-specific data value and associates a Participant, Experiment
(from DataValue), the round in which the data value was associated.
"""
class ParticipantRoundDataValue(DataValue):
    round_data = models.ForeignKey(RoundData, related_name='participant_data_values')
    participant = models.ForeignKey(Participant, related_name='round_data_values')

    def __init__(self, *args, **kwargs):
        super(ParticipantRoundDataValue, self).__init__(*args, **kwargs)
        if not hasattr(self, 'experiment'):
            self.experiment = self.round_data.experiment

    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def __unicode__(self):
        return u"data value {0}: {1} for participant {2}".format(self.parameter, self.value, self.participant)

    class Meta:
        ordering = [ 'round_data', 'participant', 'parameter' ]

class ActivityLog(models.Model):
    log_message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u"%s: %s" % (self.date_created, self.log_message)

class GroupActivityLog(ActivityLog):
    group = models.ForeignKey(Group, related_name='activity_log')
    round_configuration = models.ForeignKey(RoundConfiguration)

class ExperimentActivityLog(ActivityLog):
    experiment = models.ForeignKey(Experiment, related_name='activity_log')
    round_configuration = models.ForeignKey(RoundConfiguration)

def is_experimenter(user, experimenter=None):
    if hasattr(user, 'experimenter') and isinstance(user.experimenter, Experimenter):
        return True if experimenter is None else user.experimenter == experimenter
    return False

def is_participant(user):
    return hasattr(user, 'participant') and isinstance(user.participant, Participant)

