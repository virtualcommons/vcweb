from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.aggregates import Max
from string import Template
from vcweb.core import signals
import base64
import datetime
import hashlib
import logging
import random
import re

SHA1_RE = re.compile('^[a-f0-9]{40}$')

logger = logging.getLogger(__name__)

"""
Contains all data models used in the core as well as a number of helper functions.

Is getting big / unwieldy.  Should try to refactor into smaller parts, but creating models directory has
been painful due to circular imports.
"""

"""
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
        return u"Experiment Type: %s (namespace: %s, created on %s)" % (self.title, self.namespace, self.date_created)

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
    # opt in or opt out for ability to receive invitations 

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
    creator = models.ForeignKey(Experimenter)
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
                      ('ACTIVE', 'Active'),
                      ('PAUSED', 'Paused'),
                      ('ROUND_IN_PROGRESS', 'Round in progress'),
                      ('COMPLETED', 'Completed'))
    authentication_code = models.CharField(max_length=32, default="vcweb.auth.code")
    current_round_sequence_number = models.PositiveIntegerField(default=0)
    experimenter = models.ForeignKey(Experimenter)
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
        return self.current_round_elapsed_time > self.current_round.duration

    @property
    def time_remaining(self):
        return 100
        #return self.current_round_duration - self.current_round_elapsed_time

    @property
    def channel_name(self):
        return "%s.%s" % (self.namespace, self.id)

    def parameters(self, scope=None):
        ps = self.experiment_metadata.parameters
        return ps.filter(scope=scope) if scope else ps

    def activate(self):
        if not self.is_running():
            self.allocate_groups()
            self.status = 'ACTIVE'
            self.save()
        return self


    def allocate_groups(self, randomize=True):
        # seed the initial group.
        current_group = self.groups.create(number=1, max_size=self.experiment_configuration.max_group_size)
        # FIXME: replace with post_save hook
        current_group.initialize()
        if randomize:
            participants = list(self.participants.all())
            random.shuffle(participants)
        else:
            participants = self.participants.all()


        for p in participants:
            if current_group.is_full:
                current_group = self.groups.create(number=current_group.number + 1,
                        max_size=current_group.max_size)
            current_group.add_participant(p)

        # XXX: if there a performance hit here, should probably do a void return instead
        # or collect the groups as they are added
        return self.groups

    def is_running(self):
        return self.status != 'INACTIVE'

    def get_round_configuration(self, sequence_number):
        return self.experiment_configuration.round_configurations.get(sequence_number=sequence_number)

    def get_template_path(self, name):
        return "%s/%s" % (self.namespace, name)

    @property
    def current_round_template(self):
        return self.current_round.template_path

    @property
    def current_round(self):
        return self.get_round_configuration(self.current_round_sequence_number)

    @property
    def next_round(self):
        return self.get_round_configuration(self.current_round_sequence_number + 1)

    @property
    def previous_round(self):
        return self.get_round_configuration(self.current_round_sequence_number - 1)

    @property
    def has_next_round(self):
        return self.current_round_sequence_number < self.experiment_configuration.final_sequence_number

    @property
    def is_last_round(self):
        return self.current_round_sequence_number == self.experiment_configuration.final_sequence_number

    def advance_to_next_round(self):
        self.current_round_elapsed_time = 0
        self.current_round_sequence_number += 1
        self.save()
        # would return self work as well?
        # return self
        return Experiment.objects.get(pk=self.pk)

    def start_round(self, sender=None):
        self.status = 'ROUND_IN_PROGRESS'
        self.save()
        sender = self.experiment_metadata.pk if sender is None else sender
        # notify registered game handlers
        logger.debug("About to send round started signal with sender %s" % sender)
        return signals.round_started.send(sender, experiment_id=self.id, time=datetime.datetime.now(), round_configuration_id=self.current_round.id)

    def end_round(self, sender=None):
        self.status = 'ACTIVE'
        self.save()
        sender = self.experiment_metadata.pk if sender is None else sender
        logger.debug("about to send round ended signal with sender %s" % sender)
        return signals.round_ended.send(sender, experiment_id=self.pk)

    def check_elapsed_time(self):
        if self.is_time_expired:
            self.end_round()


    """ returns a fresh copy of this experiment with configuration / metadata intact """
    def clone(self, experimenter=None):
        if not experimenter:
            experimenter = self.experimenter
        return Experiment(experimenter=experimenter,
                          authentication_code=self.authentication_code,
                          experiment_metadata=self.experiment_metadata,
                          experiment_configuration=self.experiment_configuration,
                          duration=self.duration,
                          tick_duration=self.tick_duration,
                          is_experimenter_driven=self.is_experimenter_driven
                          )

    @property
    def url(self, request):
        user = request.user
        if user.is_authenticated():
            return "/{0}/{1}".format("participant" if is_participant(user) else "experimenter", self.url_id)
        else:
            return self.namespace


    @property
    def participant_url(self):
        return "/%s/participate" % (self.url_id)

    @property
    def management_url(self):
        return "/%s/experimenter" % (self.url_id)

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    @property
    def url_id(self):
        return "%s/%s" % (self.experiment_metadata.namespace, self.id)

    def __unicode__(self):
        return u"%s (status: %s, last updated on %s)" % (self.experiment_metadata.title, self.status, self.last_modified)

    def ___eq___(self, other):
        return self.id == other.id

    def ___cmp___(self, other):
        return self.id.___cmp___(other.id)

    def ___hash___(self):
        return self.id.___hash___()

class RoundConfiguration(models.Model):
    ROUND_TYPES = dict(BASIC=('Regular interactive experiment round', 'participate.html'),
                       CHAT=('Chat round', 'chat.html'),
                       DEBRIEFING=('Debriefing round', 'debriefing.html'),
                       INSTRUCTIONS=('Instructions round', 'instructions.html'),
                       PRACTICE=('Practice round', 'practice.html'),
                       QUIZ=('Quiz round', 'quiz.html'))
    (BASIC, CHAT, DEBRIEFING, INSTRUCTIONS, PRACTICE, QUIZ) = sorted(ROUND_TYPES.keys())

    ROUND_TYPE_CHOICES = [(round_type, ROUND_TYPES[round_type][0]) for round_type in sorted(ROUND_TYPES.keys())]

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
                                  default=BASIC)
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
        return self.template_name if self.template_name else RoundConfiguration.ROUND_TYPES[self.round_type][1]

    @property
    def template_path(self):
        return "%s/%s" % (self.experiment_configuration.namespace, self.custom_template_name)

    @property
    def round_number(self):
        return self.sequence_number if self.display_number == 0 else self.display_number

    @property
    def is_debriefing_round(self):
        return self.round_type == 'DEBRIEFING'

    @property
    def is_chat_round(self):
        return self.round_type == 'CHAT'

    @property
    def is_instructions_round(self):
        return self.round_type == 'INSTRUCTIONS'

    @property
    def is_quiz_round(self):
        return self.round_type == 'QUIZ'

    def get_parameter(self, name):
        return self.round_parameter_values.get(parameter__name=name)

    def set_parameter(self, name=None, value=None):
        parameter_value = self.round_parameter_values.get(parameter__name=name)
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
        return u"Round %d (displayed as: %d) for %s" % (self.sequence_number, self.round_number, self.experiment_configuration)

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
                  'boolean': lambda x: x or x == 'True'
                  }

    GROUP_SCOPE = 'group'
    PARTICIPANT_SCOPE = 'participant'
    ROUND_SCOPE = 'round'
    EXPERIMENT_SCOPE = 'experiment'

    SCOPE_CHOICES = ((ROUND_SCOPE, 'This parameter applies just for this round'),
                     (EXPERIMENT_SCOPE, 'This parameter applies to this entire experiment'),
                     (GROUP_SCOPE, 'Group data parameter'),
                     (PARTICIPANT_SCOPE, 'Participant data parameter'))

    scope = models.CharField(max_length=32, choices=SCOPE_CHOICES, default='round')
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)
    default_value = models.CharField(max_length=255, null=True, blank=True)
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

    @property
    def default(self):
        return self.convert(self.default_value)

    def __unicode__(self):
        return u"%s: %s (%s)" % (self.experiment_metadata.namespace, self.name, self.type)

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
        return getattr(self, self.parameter.value_field_name)

    @value.setter
    def value(self, obj):
        converted_value = self.parameter.convert(obj)
        setattr(self, self.parameter.value_field_name, converted_value)

    class Meta:
        abstract = True

class RoundParameterValue(ParameterizedValue):
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_parameter_values')

    def __unicode__(self):
        return u"{0} -> [{1}: {2}]".format(self.round_configuration, self.parameter, self.value)


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

    def initialize(self, group_round_data=None):
        if not (group_round_data and self.round_data.filter(round=self.current_round)):
            group_round_data = self.round_data.create(round=self.current_round)
        group_round_data.initialize_data_parameters()

    '''
    Not as efficient as a simple SQL update because we need to do some type
    conversion / processing to put the value into the appropriate field.
    '''
    def set_data_value(self, parameter_name=None, parameter=None, value=None):
        data_value = self.get_data_value(parameter_name=parameter_name,
                parameter=parameter)
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
        updated_rows = self.current_round_data.data_values.filter(parameter=parameter).update(**update_dict)
        if updated_rows != 1:
            logger.error("Updated %s rows, should have been only one..." % updated_rows)
        '''
        data_value = self.current_round_data.data_values.get(parameter=parameter)
        data_value.value += amount
        data_value.save()
        '''


    def get_scalar_data_value(self, parameter_name=None, parameter=None):
        return self.get_data_value(parameter_name, parameter).value

    def get_data_value(self, parameter_name=None, parameter=None):
        criteria = dict([('parameter', parameter) if parameter else ('parameter__name', parameter_name)],
                group_round_data=self.current_round_data)

        return GroupRoundDataValue.objects.get(**criteria)

    def get_group_data_values(self, name=None, *names):
        group_round_data = self.current_round_data
        if names:
            if name: names.append(name)
            return GroupRoundDataValue.objects.filter(group_round_data=group_round_data, parameter__name__in=names)
        elif name:
            return GroupRoundDataValue.objects.get(group_round_data=group_round_data, parameter__name=name)
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
            for p in self.parameters:
                self.transfer_parameter(p, value)
        else:
            self.transfer_parameter(parameter, value)

    def transfer_parameter(self, parameter, value):
        next_round_data = self.round_data.create(round=self.experiment.next_round)
# if value is set, use it, otherwise use the current round parameter value
        return next_round_data.data_values.create(parameter=parameter, experiment=self.experiment, value=value)

    def get_participant_data_value(self, participant, parameter):
        return ParticipantDataValue.objects.get(participant=participant, parameter=parameter, round_configuration=self.current_round)

    def get_participant_data_values(self, name=None, *names):
        return ParticipantDataValue.objects.filter(round_configuration=self.current_round, participant__in=self.participants.all())

    @property
    def data_parameters(self):
        return Parameter.objects.filter(experiment_metadata=self.experiment.experiment_metadata, scope=Parameter.GROUP_SCOPE)

    @property
    def current_round_data(self):
        group_round_data, just_created = GroupRoundData.objects.get_or_create(group=self, round=self.current_round)
        if just_created:
            self.initialize(group_round_data)
        return group_round_data

    @property
    def current_round_data_values(self, **kwargs):
        return self.current_round_data.data_values

    @property
    def is_full(self):
        return self.size >= self.max_size

    @property
    def is_open(self):
        return self.size < self.max_size

    def create_next_group(self):
        group = Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment)
        # FIXME: connect this to post save
        group.initialize()
        return group


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
        return u"Group #{0} in {1}".format(self.number, self.experiment)

    class Meta:
        ordering = ['experiment', 'number']


"""
Data values stored for a particular group in a particular round.
"""
class GroupRoundData (models.Model):
    group = models.ForeignKey(Group, related_name='round_data')
    round = models.ForeignKey(RoundConfiguration, related_name='group_data')
    """ show instructions before the round begins? """
    show_instructions = models.BooleanField(default=True)
    """ show debriefing after the round ends? """
    show_debriefing = models.BooleanField(default=False)
    elapsed_time = models.PositiveIntegerField(default=0)

    def initialize_data_parameters(self):
        for group_data_parameter in self.group.data_parameters:
            # create a fresh GroupRoundDataValue for each data parameter
            logger.debug("Creating parameter %s" % group_data_parameter)
            self.data_values.create(parameter=group_data_parameter, experiment=self.group.experiment)

    def __unicode__(self):
        return u"Round Data for {0} in {1}".format(self.group, self.round)



class GroupRoundDataValue(DataValue):
    group_round_data = models.ForeignKey(GroupRoundData, related_name='data_values')
    def __unicode__(self):
        return u"data value {0}: {1} for group {2}".format(self.parameter, self.value, self.group_round_data.group)
    class Meta:
        ordering = [ 'parameter' ]

class Participant(CommonsUser):
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participants')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participants')

    def set_data_value(self, experiment=None, parameter=None, value=None):
        if experiment and parameter and value:
            participant_data_value = ParticipantDataValue.objects.get(parameter=parameter,
                    experiment=experiment, participant=self, round_configuration=experiment.current_round)
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

    @property
    def active_experiments(self):
        return self.experiment_relationships.filter(experiment__status='ACTIVE')

    @property
    def inactive_experiments(self):
        return self.experiment_relationships.exclude(experiment__status='ACTIVE')

    def experiments_with_status(self, status):
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

    def __init__(self, *args, **kwargs):
        super(ParticipantExperimentRelationship, self).__init__(*args, **kwargs)
        self.generate_identifier()

    """ generates a unique identifier for the given participant and experiment stored in this relationship """
    def generate_identifier(self):
        """ set participant_identifier if it hasn't been set already.  """
        if not self.participant_identifier:
            sha1 = hashlib.sha1()
            sha1.update("%s%i%s" % (self.participant.user.email, self.experiment.id, self.date_created))
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
    participant = models.ForeignKey(Participant)
    group = models.ForeignKey(Group, related_name = 'participant_group_relationships')
    round_joined = models.ForeignKey(RoundConfiguration)
    date_joined = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    objects = ParticipantGroupRelationshipManager()

    def __unicode__(self):
        return u"{0}: {1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['participant_number', 'participant']

class ChatMessage(models.Model):
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='chat_messages')
    message = models.CharField(max_length=512)
    """ if set, this is a targeted message to the other participant in this group.  If null, this is a broadcast message to the entire group """
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True, related_name='targets')
    date_created = models.DateTimeField(auto_now_add=True)
    ''' the round in which this message was sent '''
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='chat_messages')
    ''' the experiment in which this message was sent, not strictly necessary '''
    experiment = models.ForeignKey(Experiment, related_name='chat_messages')

    def __unicode__(self):
        """ return this participant's sequence number combined with the message """
        participant_number = self.participant_group_relationship.participant_number
        return u"{0}: {1}".format(participant_number, self.message)
"""
The particular participant data value for a given ParticipantRoundData (round + participant entity)
"""
class ParticipantDataValue(DataValue):
    participant = models.ForeignKey(Participant, related_name='data_values')
    round_configuration = models.ForeignKey(RoundConfiguration)

    class Meta:
        ordering = [ 'parameter' ]

class SessionData(models.Model):
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField()
    experimenter = models.ForeignKey(Experimenter, related_name='sessions')
    participant = models.ForeignKey(Participant, related_name='sessions')
    group = models.ForeignKey(Group, related_name='sessions')

class ActivityLog(models.Model):
    log_message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)

class GroupActivityLog(ActivityLog):
    group = models.ForeignKey(Group, related_name='activity_log')
    round_configuration = models.ForeignKey(RoundConfiguration)

def is_experimenter(user):
    return hasattr(user, 'experimenter') and isinstance(user.experimenter, Experimenter)

def is_participant(user):
    return hasattr(user, 'participant') and isinstance(user.participant, Participant)
