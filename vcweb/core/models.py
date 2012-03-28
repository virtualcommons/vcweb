from datetime import datetime
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.aggregates import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.html import escape
from django.utils.timesince import timesince
from string import Template
from vcweb.core import signals, simplecache

import base64
import hashlib
import logging
import random
import re
import simplejson

logger = logging.getLogger(__name__)

"""
Contains all data models used in the core as well as a number of helper functions.
FIXME: getting a bit monolithically unwieldy.  Consider splitting into models subdirectory
"""

@receiver(signals.minute_tick, sender=None)
def minute_tick_handler(sender, time=None, **kwargs):
    """
    handles each minute tick
    """
    logger.debug("handling minute tick signal at %s with kwargs %s", time, kwargs)
    # inspect all active experiments and update their time left
    Experiment.objects.increment_elapsed_time(status='ROUND_IN_PROGRESS')

class ExperimentMetadataManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(namespace=key)

class ExperimentMetadata(models.Model):
    """
    An ExperimentMetadata record represents the *type* of a given implemented Experiment, e.g., **Forestry** or
    **Irrigation**.  This shouldn't be confused with a **Forestry** or **Irrigation** Experiment instance, which
    represents a concrete experiment run, with a specific configuration, experimenter, etc.  Each experiment app
    should define and add a single ExperimentMetadata record for the experiment type that it represents.  You can
    register an ExperimentMetadata object by creating a JSON/YAML/SQL representation of it in your app/fixtures
    directory (e.g., irrigation/fixtures/irrigation.json) and then invoking ``python manage.py loaddata irrigation``.
    """
    title = models.CharField(max_length=255)
    # the URL fragment that this experiment_metadata will occupy,
    namespace_regex = re.compile(r'^(?:[/]?[a-z0-9_]+\/?)+$')
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=namespace_regex)])
    # short name slug
    short_name = models.SlugField(max_length=32, unique=True, null=True)
    description = models.TextField(null=True, blank=True)
# FIXME: convert to DateTimeField
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
    Base class for both Participants and Experimenters.  The actual participant or experimenter can be resolved as
    user.participant or user.experimenter due to the OneToOne with django.contrib.User.
    """
    user = models.OneToOneField(User, related_name='%(class)s', verbose_name=u'Django User', unique=True)
    failed_password_attempts = models.PositiveIntegerField(default=0)
    institution = models.ForeignKey(Institution, null=True, blank=True)
    authentication_token = models.CharField(max_length=64, null=True, blank=True)

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

    @property
    def last_login(self):
        return self.user.last_login

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
    """
    The configuration for a given Experiment instance.  One ExperimentConfiguration can be applied to many Experiment
    instances but can only be associated to a single ExperimentMetadata record.  
    """
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='experiment_configuration_set')
    creator = models.ForeignKey(Experimenter, related_name='experiment_configuration_set')
    name = models.CharField(max_length=255)
    max_number_of_participants = models.PositiveIntegerField(default=0)
# FIXME: convert to DateTimeField uniformly
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)
    max_group_size = models.PositiveIntegerField(default=5)

    @property
    def final_sequence_number(self):
        # FIXME: or max round_configurations.sequence_number (degenerate data)
        return self.round_configuration_set.count()

    @property
    def last_round_sequence_number(self):
        return self.round_configuration_set.aggregate(sequence_number=Max('sequence_number'))['sequence_number']

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    def __unicode__(self):
        return u"%s configuration for the %s" % (self.name, self.experiment_metadata)

    class Meta:
        ordering = ['experiment_metadata', 'creator', 'date_created']


class ExperimentManager(models.Manager):
    def get_all_active(self):
        return self.filter(status='ACTIVE')

    def increment_elapsed_time(self, status='ROUND_IN_PROGRESS', amount=60):
        if status is not None:
            es = self.filter(status=status)
            es.update(current_round_elapsed_time=models.F('current_round_elapsed_time') + amount,
                    total_elapsed_time=models.F('total_elapsed_time') + amount)
            # check each experiment's total_elapsed_time against the total allotted time and
            # issue round_stopped signals to experiments that need to be stopped.
            for experiment in es.all():
                logger.debug("checking elapsed time on experiment %s", experiment)
                experiment.check_elapsed_time()

class Experiment(models.Model):
    """
    Experiment instances are a concrete parameterization of an ExperimentMetadata record, with associated
    ExperimentConfiguration, Experimenter, etc.  In other words, they represent an actual experiment run.
    """
    STATUS_CHOICES = (('INACTIVE', 'Not active'),
                      ('ACTIVE', 'Active, no round in progress'),
                      ('PAUSED', 'Paused'),
                      ('ROUND_IN_PROGRESS', 'Round in progress'),
                      ('COMPLETED', 'Completed'))
    (INACTIVE, ACTIVE, PAUSED, ROUND_IN_PROGRESS, COMPLETED) = [ choice[0] for choice in STATUS_CHOICES ]
    authentication_code = models.CharField(max_length=32, default="vcweb.auth.code")
    """
    currently unused, but kept here in the event that we want to allow participants to authenticate with this
    authentication_code either in lieu or in addition to their own user password.
    """
    current_round_sequence_number = models.PositiveIntegerField(default=1)
    """ Each round is assigned a sequential sequence number, ranging from 1 to N.  Used to identify which round the
    experiment is currently running. """
    experimenter = models.ForeignKey(Experimenter)
    """ the user running this experiment """
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    """ the experiment metadata object that this experiment instance represents """
    experiment_configuration = models.ForeignKey(ExperimentConfiguration)
    """ the configuration parameters in use for this experiment run. """
    status = models.CharField(max_length=32, choices=STATUS_CHOICES,
                              default='INACTIVE')
    """
    the status of an experiment can be either INACTIVE, ACTIVE, PAUSED, ROUND_IN_PROGRESS, or COMPLETED
    """
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    start_date_time = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format
    # 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32, null=True, blank=True)
    tick_duration = models.CharField(max_length=32, null=True, blank=True)
    """ how often the experiment_metadata server should tick. """

    total_elapsed_time = models.PositiveIntegerField(default=0)
    """
    total elapsed time in seconds since this experiment_metadata was
    started, incremented by the heartbeat monitor.
    """
    current_round_start_time = models.DateTimeField(null=True, blank=True)
    """ current round start time """
    current_round_elapsed_time = models.PositiveIntegerField(default=0)
    """ elapsed time in seconds for the current round. """
    is_experimenter_driven = models.BooleanField(default=True)
    """
    Experimenter driven experiments have checkpoints where the experimenter
    needs to explicitly signal the system to move to the next round or stage.
    """
    amqp_exchange_name = models.CharField(max_length=64, default="vcweb.default.exchange")

    slug = models.SlugField(max_length=16, unique=True, null=True, blank=True)
    ''' short slug to use instead of experiment pk, currently unimplemented '''

    objects = ExperimentManager()

    @property
    def is_time_expired(self):
        return self.current_round_elapsed_time >= self.current_round.duration

    @property
    def is_round_in_progress(self):
        return self.status == 'ROUND_IN_PROGRESS'

    @property
    def is_data_round_in_progress(self):
        return self.is_round_in_progress and self.current_round.is_playable_round

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
    def sequence_label(self):
        return u"Round %s of %s" % (self.current_round_sequence_number, self.experiment_configuration.final_sequence_number)

    @property
    def status_line(self):
        return u"%s #%s (%s), %s" % (
                self.experiment_metadata.title,
                self.pk,
                self.experiment_configuration.name,
                self.sequence_label)

    @property
    def participant_group_relationships(self):
        for group in self.group_set.all():
            for pgr in group.participant_group_relationship_set.all():
                yield pgr

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

# The following URL helper properties are generic experiment management URLs
# available to experimenters but not participants
    @property
    def management_url(self):
        return "/%s/experimenter" % self.get_absolute_url()

    @property
    def configure_url(self):
        return "/%s/configure" % self.get_absolute_url()

    @property
    def stop_url(self):
        return "%s/stop" % self.controller_url

    @property
    def monitor_url(self):
        return "%s/monitor" % self.controller_url

    @property
    def clone_url(self):
        return "%s/clone" % self.controller_url

    @property
    def controller_url(self):
        return "/experiment/%s" % self.pk

    @property
    def participant_url(self):
        return "/%s/participate" % self.get_absolute_url()

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
        round_data, created = self.round_data_set.get_or_create(round_configuration=self.current_round)
        return round_data

    @property
    def playable_round_data(self):
        return self.round_data_set.select_related(depth=1).filter(round_configuration__round_type__in=RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS,
                round_configuration__sequence_number__lte=self.current_round_sequence_number)

    @property
    def all_quiz_questions(self):
        # FIXME: use generator expression?
        quiz_questions = list(self.default_quiz_questions.all())
        quiz_questions.extend(self.current_round.quiz_questions.all())
        return quiz_questions

    @property
    def current_round_quiz_questions(self):
        return self.current_round.quiz_questions

    @property
    def next_round(self):
       if self.has_next_round:
          return self.get_round_configuration(self.current_round_sequence_number + 1)
       else:
          return self.current_round

    @property
    def next_round_instructions(self):
        if self.has_next_round:
            return self.next_round.instructions
        else:
            return u'This is the final round.'

    @property
    def previous_round(self):
        # FIXME: loop instead w/ mod?
        return self.get_round_configuration(max(self.current_round_sequence_number - 1, 1))

    @property
    def has_next_round(self):
        return self.current_round_sequence_number < self.experiment_configuration.final_sequence_number

    @property
    def is_last_round(self):
        return self.current_round_sequence_number == self.experiment_configuration.final_sequence_number

    @property
    def is_active(self):
        return self.status != 'INACTIVE'

    @property
    def actions_help_text(self):
        if hasattr(self, 'custom_help_text'):
            return self.custom_help_text['actions']
        # return dynamic text based on current_round?
        return self.current_round.instructions

    @property
    def all_participants_have_submitted(self):
        pdvs = self.current_round_data.participant_data_value_set
        return pdvs.filter(submitted=False).count() == 0

    def register_participants(self, users=None, emails=None, institution=None, password=None):
        if self.participant_set.count() > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, self.participant_set.count())
            return
        if users is None:
            users = []
            if emails is None:
                logger.warning("No users or emails supplied, aborting.")
                return
            if password is None:
                password = self.authentication_code
            for email in emails:
                try:
                    u = User.objects.get(username=email)
                except User.DoesNotExist:
                    u = User.objects.create_user(username=email, email=email, password=password)
                users.append(u)
        for user in users:
            #logger.debug("registering user %s", user)
            (p, created) = Participant.objects.get_or_create(user=user)
            # FIXME: instead of asking for the email suffix, perhaps we just append the institution URL to keep it simpler?
            if institution and p.institution != institution:
                p.institution = institution
                p.save()
            ParticipantExperimentRelationship.objects.create(participant=p, experiment=self, created_by=self.experimenter.user)


    ''' hardcoded defaults for the slovakia pretest '''
    def setup_test_participants(self, count=20, institution=None, email_suffix='sav.sk', password='test'):
        if self.participant_set.count() > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, self.participant_set.count())
            return
        users = []
        for i in xrange(1, count+1):
            email = u's%d@%s' % (i, email_suffix)
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                user = User.objects.create_user(username=email, email=email, password=password)
                user.first_name = u'Student'
                user.last_name = u"%d" % i
                user.save()
            users.append(user)
        self.register_participants(users=users, institution=institution)

    def initialize_parameters(self, group_parameters=None, participant_parameters=None):
        if not self.current_round.is_playable_round:
            logger.warn("ignoring request to initialize parameters for round %s", self.current_round)
            return
        if group_parameters is None:
            group_parameters = self.parameters(scope=Parameter.GROUP_SCOPE)
        if participant_parameters is None:
            participant_parameters = self.parameters(scope=Parameter.PARTICIPANT_SCOPE)
        current_round_data = self.current_round_data
        for group in self.group_set.select_related(depth=1).all():
            for parameter in group_parameters:
                group_data_value, created = current_round_data.group_data_value_set.get_or_create(group=group, parameter=parameter)
                logger.debug("%s (%s)", group_data_value, created)
            if participant_parameters:
                for pgr in group.participant_group_relationship_set.all():
                    for parameter in participant_parameters:
                        participant_data_value, created = current_round_data.participant_data_value_set.get_or_create(participant_group_relationship=pgr, parameter=parameter)
                        logger.debug("%s (%s)", participant_data_value, created)

    def log(self, log_message):
        if log_message:
            logger.debug("%s: %s", self, log_message)
            self.activity_log_set.create(round_configuration=self.current_round, log_message=log_message)

    def data_file_name(self, file_ext='csv'):
        return "%s_%s_%s.%s" % (slugify(self.experiment_metadata.title), self.pk, datetime.now().strftime("%d-%m-%y-%H%M"), file_ext)

    def parameters(self, scope=None):
        parameter_set = self.experiment_metadata.parameter_set
        return parameter_set.filter(scope=scope) if scope else parameter_set

    def activate(self):
        if not self.is_active:
            self.allocate_groups()
            self.status = 'ACTIVE'
            self.save()
        return self

    def allocate_groups(self, randomize=True):
        # clear out all existing groups
        # FIXME: record previous mappings in activity log.
        self.group_set.all().delete()
        # seed the initial group.
        max_group_size = self.experiment_configuration.max_group_size
        logger.debug("creating group with max size %d", max_group_size)
        current_group = self.group_set.create(number=1, max_size=max_group_size)
        participants = list(self.participant_set.all())
        if randomize:
            random.shuffle(participants)

        for p in participants:
            if current_group.is_full:
                current_group = current_group.create_next_group()
            current_group.add_participant(p)

        # XXX: if there a performance hit here, should probably do a void return instead
        # or collect the groups as they are added
        return self.group_set

    def get_round_configuration(self, sequence_number):
        return self.experiment_configuration.round_configuration_set.get(sequence_number=sequence_number)

    def get_template_path(self, name):
        return "%s/%s" % (self.namespace, name)

    # XXX: decide whether or not to include this ability in the interface.
    def move_to_previous_round(self):
        if self.is_round_in_progress:
            self.end_round()
        self.current_round_elased_time = 0
        self.current_round_sequence_number = max(self.current_round_sequence_number - 1, 1)
        self.save()

    def advance_to_next_round(self):
        if self.is_round_in_progress:
            self.end_round()
        if self.has_next_round:
            self.current_round_elapsed_time = 0
            self.current_round_sequence_number += 1
            self.start_round()
        else:
            logger.warning("trying to advance past the last round - no-op")

    def start_round(self, sender=None):
        self.status = 'ROUND_IN_PROGRESS'
        self.current_round_data
        self.current_round_elapsed_time = 0
        self.current_round_start_time = datetime.now()
        self.save()
        self.log('Starting round')
        # FIXME: would prefer using self.namespace as a default but django's
        # managed unicode strings don't work as senders
        sender = self.experiment_metadata.pk if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        # notify registered game handlers
        logger.debug("About to send round started signal with sender %s", sender)
        return signals.round_started.send(sender, experiment=self, time=datetime.now(), round_configuration=self.current_round)

    def end_round(self, sender=None):
        self.status = 'ACTIVE'
        self.current_round_elapsed_time = max(self.current_round_elapsed_time, self.current_round.duration)
        self.save()
        self.log('Ending round with elapsed time %s' % self.current_round_elapsed_time)
        sender = self.experiment_metadata.pk if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        logger.debug("about to send round ended signal with sender %s", sender)
        return signals.round_ended.send(sender, experiment=self, round_configuration=self.current_round)

    def stop(self):
        self.log("Stopping experiment and flagging as inactive.")
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

    def transfer_participants(self, experiment):
        if experiment.participant_set.count() == 0:
            for participant in self.participant_set.all():
                ParticipantExperimentRelationship.objects.create(participant=participant,
                        experiment=experiment, created_by=self.experimenter.user)
        else:
            logger.warning("Tried to transfer participants to an experiment %s that already had participants %s", experiment, experiment.participant_set.all())

    def __unicode__(self):
        return u"%s #%s | %s" % (self.experiment_metadata.title, self.pk, self.experimenter)

    class Meta:
        ordering = ['date_created', 'status']

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
    PLAYABLE_ROUND_CONFIGURATIONS = (PRACTICE, REGULAR)

    experiment_configuration = models.ForeignKey(ExperimentConfiguration, related_name='round_configuration_set')
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
    def is_playable_round(self):
        return self.round_type in RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS

    def get_parameter(self, name):
        parameter = Parameter.objects.get(name=name, scope=Parameter.ROUND_SCOPE)
        round_parameter, created = self.round_parameter_value_set.get_or_create(parameter=parameter)
        if created:
            logger.debug("created new parameter %s for %s", parameter, self)
        return round_parameter

    def set_parameter(self, name=None, value=None):
        parameter = Parameter.objects.get(name=name, scope=Parameter.ROUND_SCOPE)
        parameter_value, created = self.round_parameter_value_set.get_or_create(parameter=parameter)
        parameter_value.value = value
        parameter_value.save()

    def get_parameter_value(self, name, default=None):
        try:
            return self.round_parameter_value_set.get(parameter__name=name).value
        except RoundParameterValue.DoesNotExist:
            return default

    def get_debriefing(self, participant_id=None, **kwargs):
        return self.templatize(self.debriefing, participant_id, kwargs)

    def get_instructions(self, participant_id=None, **kwargs):
        return self.templatize(self.instructions, participant_id, kwargs)


    def templatize(self, template_string, participant_id=None, **kwargs):
        return Template(template_string).substitute(kwargs, round_number=self.display_number, participant_id=participant_id)

    def __unicode__(self):
        return u"%s (%s)" % (self.display_label, self.sequence_label)

    @property
    def display_label(self):
        return u"Round %d" % self.round_number if self.is_regular_round else self.get_round_type_display()

    @property
    def sequence_label(self):
        return u"%d of %d" % (self.sequence_number, self.experiment_configuration.final_sequence_number)

    class Meta:
        ordering = [ 'experiment_configuration', 'sequence_number', 'date_created' ]

class QuizQuestion(models.Model):
    label = models.CharField(max_length=512)
    answer = models.CharField(max_length=64)
    input_type = models.CharField(max_length=32)
    explanation = models.CharField(max_length=512)
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='quiz_question_set')
    experiment = models.ForeignKey(Experiment, related_name='default_quiz_question_set', null=True, blank=True)

    def is_correct(self, candidate):
        return self.answer == candidate

    def __unicode__(self):
        return u'%s' % self.label

class ParameterManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Parameter(models.Model):
    PARAMETER_TYPES = (('int', 'Integer value'),
                       ('string', 'String value'),
                       ('float', 'Float value'),
                       ('boolean', (('True', True), ('False', False))),
                       ('enum', 'Enumeration'))

    NONE_VALUES_DICT = dict(map(lambda x,y: (x[0], y), PARAMETER_TYPES, [0, '', 0.0, False, None]))
    #dict(zip([parameter_type[0] for parameter_type in PARAMETER_TYPES], [0, '', 0.0, False, None]))

    CONVERTERS = {
            'int': int,
            'string':str,
            'float': float,
            'boolean': lambda x: bool(x) and str(x).lower() != 'false'
            }
    '''
    all converters are one-arg functions that convert string input into
    the appropriate data type.
    NOTE: they expect already validated string data and will throw ValueErrors
    on invalid input.
    '''

    GROUP_SCOPE = 'group'
    GROUP_ROUND_SCOPE = 'group_round'
    PARTICIPANT_SCOPE = 'participant'
    ROUND_SCOPE = 'round'
    EXPERIMENT_SCOPE = 'experiment'

    SCOPE_CHOICES = ((ROUND_SCOPE, 'Parameter applies just for this round'),
                     (EXPERIMENT_SCOPE, 'Parameter applies to this entire experiment'),
                     (GROUP_SCOPE, 'Parameter applies to the entire group for the duration of the experiment'),
                     (GROUP_ROUND_SCOPE, 'Parameter applies to the entire group for a given round'),
                     (PARTICIPANT_SCOPE, 'Parameter is for a single participant'))

    scope = models.CharField(max_length=32, choices=SCOPE_CHOICES, default=ROUND_SCOPE)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField(max_length=512, null=True, blank=True)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)
    default_value_string = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    creator = models.ForeignKey(Experimenter)
    experiment_metadata = models.ForeignKey(ExperimentMetadata, null=True, blank=True)
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
        return u"%s (%s) scope:%s" % (self.label, self.type, self.scope)

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'experiment_metadata', 'scope')

class ParameterizedValue(models.Model):
    """
    Supertype for GroupRoundDataValue and ParticipantRoundDataValue
    """
    parameter = models.ForeignKey(Parameter)
    string_value = models.TextField(null=True, blank=True)
    int_value = models.IntegerField(null=True, blank=True)
    float_value = models.FloatField(null=True, blank=True)
    boolean_value = models.NullBooleanField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    @property
    def value(self):
        value = getattr(self, self.parameter.value_field_name, self.parameter.none_value)
        return value if value is not None else self.parameter.none_value

    @value.setter
    def value(self, obj):
        converted_value = self.parameter.convert(obj)
        setattr(self, self.parameter.value_field_name, converted_value)

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2}".format(self.parameter, self.value, self.date_created)

    class Meta:
        abstract = True

class RoundParameterValue(ParameterizedValue):
    """
    Represents a specific piece of round configuration data.
    """
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_parameter_value_set')

    def __unicode__(self):
        return u"{0} -> [{1}: {2}]".format(self.round_configuration, self.parameter, self.value)

class Group(models.Model):
    number = models.PositiveIntegerField()
    ''' internal numbering unique to the given experiment '''
    max_size = models.PositiveIntegerField(default=5)
    """
    how many members can this group hold at a maximum? Could be specified as a
    RoundParameterValue / ExperimentConfiguration value
    """
    experiment = models.ForeignKey(Experiment)
    """
    The experiment that contains this Group.
    """

    @property
    def channel(self):
        """ should return a unique chat / event channel to communicate on """
        return u"%s.%d" % (self.experiment.event_channel_name, self.number)

    @property
    def experiment_channel(self):
        return self.experiment.event_channel_name

    @property
    def size(self):
        return self.participant_set.count()

    @property
    def current_round(self):
        return self.experiment.current_round

    @property
    def all_participants_str(self):
        return ', '.join([participant.email for participant in self.participant_set.all()])

    @property
    def data_parameters(self):
        return Parameter.objects.filter(experiment_metadata=self.experiment.experiment_metadata, scope=Parameter.GROUP_SCOPE)

    @property
    def current_round_data(self):
        return self.experiment.current_round_data

    @property
    def current_round_data_values(self):
        return self.current_round_data.group_data_value_set

    @property
    def is_full(self):
        return self.size >= self.max_size

    @property
    def is_open(self):
        return self.size < self.max_size

    @property
    def current_round_activity_log(self):
        return self.activity_log_set.filter(round_configuration=self.current_round)

    def log(self, log_message):
        if log_message:
            logger.debug(log_message)
            self.activity_log_set.create(round_configuration=self.current_round, log_message=log_message)

    def subtract(self, parameter=None, amount=0):
        self.add(parameter, -amount)

    def add(self, parameter=None, amount=0):
# could be a float or an int..
        update_dict = { parameter.value_field_name : models.F(parameter.value_field_name) + amount }
        self.log("adding %s to this group's %s parameter" % (amount, parameter))
        '''
        vs
        GroupRoundDataValue.objects.filter(group_round_data=self.current_round_data, parameter=parameter).update(**update_dict)
        '''
        updated_rows = self.data_value_set.filter(round_data=self.current_round_data, parameter=parameter).update(**update_dict)
        if updated_rows != 1:
            logger.error("Updated %s rows, should have been only one.", updated_rows)
        '''
        data_value = self.current_round_data.data_values.get(parameter=parameter)
        data_value.value += amount
        data_value.save()
        '''
    def has_data_parameter(self, **kwargs):
        criteria = self._data_parameter_criteria(**kwargs)
        try:
            return self.data_value_set.filter(**criteria).count() > 0
        except:
            return False

    def get_scalar_data_value(self, parameter=None, parameter_name=None):
        return self.get_data_value(parameter=parameter, parameter_name=parameter_name).value

    def get_data_value(self, parameter=None, parameter_name=None, round_data=None, default=None):
        criteria = self._data_parameter_criteria(parameter=parameter, parameter_name=parameter_name, round_data=round_data)
        try:
            return self.data_value_set.get(**criteria)
        except GroupRoundDataValue.DoesNotExist as e:
            logger.warning("No data value found for criteria %s", criteria)
            if default is None:
                raise e
            else:
                return default

    def set_data_value(self, parameter_name=None, parameter=None, value=None):
        '''
        Not as efficient as a simple SQL update because we need to do some type
        conversion / processing to put the value into the appropriate field.
        '''
        data_value = self.get_data_value(parameter_name=parameter_name, parameter=parameter)
        data_value.value = value
        self.log("setting parameter %s = %s" % (parameter, value))
        data_value.save()


    def _data_parameter_criteria(self, parameter=None, parameter_name=None, round_data=None, **kwargs):
        criteria = dict([
            ('parameter', parameter) if parameter else ('parameter__name', parameter_name),
            ('round_data', self.current_round_data if round_data is None else round_data)
            ])
        criteria.update(kwargs)
        return criteria


    def get_group_data_values(self, name=None, *names):
        round_data = self.current_round_data
        if names:
            if name: names.append(name)
            return self.data_value_set.filter(round_data=round_data, parameter__name__in=names)
        elif name:
            return self.data_value_set.get(round_data=round_data, parameter__name=name)
        else:
            logger.warning("Trying to retrieve data value by name with no args")
        return None

    def transfer_to_next_round(self, parameter=None, value=None, transfer_existing_value=True):
        '''
        Transfers the given parameter to the next round.  If parameter isn't set,
        transfer all parameters to the next round.
        FIXME: If this ends up being surprising or isn't desired behavior for
        common use cases, revisit and remove.
        '''
        if self.experiment.is_last_round:
            logger.warning("Trying to transfer parameter %s to next round but this is the last round", parameter)
            return
        value = self.get_scalar_data_value(parameter=parameter) if transfer_existing_value else value
        if not parameter:
            for p in self.data_parameters:
                self.transfer_parameter(p, value)
        else:
            self.transfer_parameter(parameter, value)

    def transfer_parameter(self, parameter, value):
        if self.experiment.is_last_round:
            logger.error("Trying to transfer parameter (%s: %s) past the last round of the experiment",
                    parameter, value)
            return None
        next_round_data, created = self.experiment.round_data_set.get_or_create(round_configuration=self.experiment.next_round)
        logger.debug("next round data: %s (%s)", next_round_data, created)
        group_data_value, created = next_round_data.group_data_value_set.get_or_create(group=self, parameter=parameter, defaults={'value': value})
        logger.debug("group data value: %s (%s)", group_data_value, created)
        if not created:
            group_data_value.value = value
            group_data_value.save()
        return group_data_value

    def get_participant_data_values(self, **kwargs):
        criteria = self._data_parameter_criteria(participant_group_relationship__group=self, **kwargs)
        return ParticipantRoundDataValue.objects.filter(**criteria)


    def create_next_group(self):
        return Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment)

    """
    Adds the given participant to this group or a new group if this group is is_full.
    Returns the group the participant was added to.
    If participant is invalid, returns this group as a no-op.
    """
    def add_participant(self, participant):
        if not participant:
            logger.warning("Trying to add invalid participant %s to group %s", participant, self)
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


class RoundData(models.Model):
    """
    round-specific data for a given experiment.  Contains related sets to group_data
    (GroupRoundDataValue), participant_data (ParticipantRoundDataValue), and
    chat_messages (ChatMessage)
    """
    experiment = models.ForeignKey(Experiment, related_name='round_data_set')
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_data_set')
    elapsed_time = models.PositiveIntegerField(default=0)

    def __unicode__(self):
        return u"Data for Round %s (%s)" % (self.round_configuration.sequence_number, self.round_configuration.get_round_type_display())

    class Meta:
        ordering = [ 'round_configuration' ]

class GroupRoundDataValue(ParameterizedValue):
    group = models.ForeignKey(Group, related_name='data_value_set')
    round_data = models.ForeignKey(RoundData, related_name='group_data_value_set')

    def __init__(self, *args, **kwargs):
        super(GroupRoundDataValue, self).__init__(*args, **kwargs)
        if not hasattr(self, 'experiment'):
            self.experiment = self.round_data.experiment


    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def __unicode__(self):
        return u"{0}={1} ({2}, {3})".format(self.parameter, self.value, self.group, self.round_configuration)

    class Meta:
        ordering = [ 'round_data', 'group', 'parameter' ]


class Participant(CommonsUser):
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participant_set')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participant_set')

    @property
    def active_experiments(self):
        return self.experiment_relationship_set.filter(experiment__status=Experiment.ACTIVE)

    @property
    def inactive_experiments(self):
        return self.experiment_relationship_set.exclude(experiment__status=Experiment.ACTIVE)

    @property
    def completed_experiments(self):
        return self.experiments_with_status(Experiment.COMPLETED)

    def get_participant_experiment_relationship(self, experiment):
        return ParticipantExperimentRelationship.objects.select_related(depth=1).get(participant=self, experiment=experiment)

    def get_participant_group_relationship(self, experiment):
        return ParticipantGroupRelationship.objects.get_participant_group(self, experiment)

    def experiments_with_status(self, status=Experiment.ACTIVE):
        return self.experiment_relationship_set.filter(experiment__status=status)

    class Meta:
        ordering = ['user']


class ParticipantExperimentRelationship(models.Model):
    """
    Many-to-many relationship entity storing a participant and the experiment they are participating in.
    """
    participant = models.ForeignKey(Participant, related_name='experiment_relationship_set')
    participant_identifier = models.CharField(max_length=32)
    sequential_participant_identifier = models.PositiveIntegerField()
    experiment = models.ForeignKey(Experiment, related_name='participant_relationship_set')
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User)
    last_completed_round_sequence_number = models.PositiveIntegerField(default=0)
    current_location = models.CharField(max_length=64, null=True, blank=True)
# arbitrary JSON-encoded data
    additional_data = models.TextField(null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super(ParticipantExperimentRelationship, self).__init__(*args, **kwargs)
        self.generate_identifier()

    def generate_identifier(self):
        """
        generates a unique identifier for the given participant and experiment stored in this relationship.
        a no-op if participant_identifier is already set.
        """
        if not self.participant_identifier:
            sha1 = hashlib.sha1()
            sha1.update("%s%i%s" % (self.participant.user.email, self.experiment.pk, self.date_created))
            self.participant_identifier = base64.urlsafe_b64encode(sha1.digest())
            self.sequential_participant_identifier = ParticipantExperimentRelationship.objects.filter(experiment=self.experiment).count() + 1
        return self.participant_identifier

    def __unicode__(self):
        return u"Experiment {0} - participant {1} (created {2})".format(self.experiment, self.participant, self.date_created)

class ParticipantGroupRelationshipManager(models.Manager):

    def by_experiment(self, experiment):
        return self.select_related(depth=1).filter(group__experiment=experiment)

    def get_participant_group(self, participant, experiment):
        try:
            return self.select_related(depth=1).get(group__experiment=experiment, participant=participant)
        except ParticipantGroupRelationship.DoesNotExist:
            logger.warning("Participant %s does not belong to a group in %s", participant, experiment)
            return None

class ParticipantGroupRelationship(models.Model):
    """
    Many-to-many relationship entity storing a participant, group, their participant number in that group, the
    round in which they joined the group, and the datetime that they joined the group.
    """
# FIXME: should also add a participant_identifier field here in case we want to use something other than numbers..?
    participant_number = models.PositiveIntegerField()
    participant = models.ForeignKey(Participant, related_name='participant_group_relationship_set')
    group = models.ForeignKey(Group, related_name = 'participant_group_relationship_set')
    round_joined = models.ForeignKey(RoundConfiguration)
    date_created = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)
    notifications_since = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    objects = ParticipantGroupRelationshipManager()

    @property
    def current_round_data(self):
        return self.group.current_round_data

    @property
    def experiment(self):
        return self.group.experiment
    @property
    def group_number(self):
        return self.group.number

    def set_data_value(self, parameter=None, value=None):
        current_round_data = self.current_round_data
        if parameter is not None and value is not None:
            # FIXME: make sure this is concurrent-safe or better yet that all participant data values are created at the
            # start of a round.
            participant_data_value, created = current_round_data.participant_data_value_set.get_or_create(parameter=parameter, participant_group_relationship=self)
            participant_data_value.value = value
            # FIXME: parameterize / make explicit?
            participant_data_value.submitted = True
            participant_data_value.save()
        else:
            logger.warning("Unable to set data value %s on round data %s for %s", value, current_round_data, parameter)


    def __unicode__(self):
        return u"{0}: #{1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['group', 'participant_number']

class ParticipantRoundDataValue(ParameterizedValue):
    """
    Represents one data point collected for a given Participant in a given Round.
    """
    round_data = models.ForeignKey(RoundData, related_name='participant_data_value_set')
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='participant_data_value_set')
    submitted = models.BooleanField(default=False)
    target_data_value = models.ForeignKey('ParticipantRoundDataValue', related_name='target_data_value_set', null=True, blank=True)

    def __init__(self, *args, **kwargs):
        super(ParticipantRoundDataValue, self).__init__(*args, **kwargs)
        # FIXME: is this really necessary?
        if 'participant_group_relationship' in kwargs and not hasattr(self, 'round_data'):
            participant_group_relationship = kwargs['participant_group_relationship']
            self.round_data = participant_group_relationship.experiment.current_round_data

    @property
    def participant(self):
        return self.participant_group_relationship.participant

    @property
    def group(self):
        return self.participant_group_relationship.group

    @property
    def participant_number(self):
        return self.participant_group_relationship.participant_number

    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def __unicode__(self):
        return u"{0} : {1} for participant {2}".format(self.parameter, self.value, self.participant_group_relationship)

    class Meta:
        ordering = [ 'round_data', 'participant_group_relationship', 'parameter' ]


@simplecache
def get_chat_message_parameter():
    return Parameter.objects.get(name='chat_message', scope=Parameter.PARTICIPANT_SCOPE)

class ChatMessageManager(models.Manager):
    def message(self, experiment, message):
        current_round_data = experiment.current_round_data
        for participant in experiment.participant_set.all():
            yield ChatMessage.objects.create(participant_group_relationship=participant.get_participant_group_relationship(experiment),
                    value=message,
                    round_data=current_round_data)

class ChatMessage(ParticipantRoundDataValue):
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True, related_name='target_participant_chat_message_set')
    """ if set, this is a targeted message to the other participant in this group.  If null, this is a broadcast message to the entire group """
    objects = ChatMessageManager()

    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_chat_message_parameter()
        super(ChatMessage, self).__init__(*args, **kwargs)

    @property
    def message(self):
        return self.value

    @property
    def group(self):
        return self.participant_group_relationship.group

    @property
    def participant(self):
        return self.participant_group_relationship.participant

    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    @property
    def as_html(self):
        return "<a name='{0}'>{1}</a> | {2}".format(self.pk,
                self.date_created.strftime("%H:%M:%S"),
                self.__unicode__())

    def __unicode__(self):
        """ return this participant's sequence number combined with the message """
        participant_number = self.participant_group_relationship.participant_number
        return u"{0}: {1}".format(participant_number, self.value)

    class Meta:
        ordering = ['date_created']

@simplecache
def get_comment_parameter():
    return Parameter.objects.get(name='comment', scope=Parameter.PARTICIPANT_SCOPE)

@simplecache
def get_like_parameter():
    return Parameter.objects.get(name='like', scope=Parameter.PARTICIPANT_SCOPE)

class Comment(ParticipantRoundDataValue):
    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_comment_parameter()
        super(Comment, self).__init__(*args, **kwargs)

    def to_dict(self):
        return {'pk' : self.pk,
                'participant_group_id': self.participant_group_relationship.pk,
                'participant_name': escape(self.participant_group_relationship.participant.full_name),
                'participant_number': self.participant_group_relationship.participant_number,
                'date_created': timesince(self.date_created),
                'message': escape(self.value)
                }

    class Meta:
        ordering = ['date_created']

class Like(ParticipantRoundDataValue):
    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_like_parameter()
        super(Like, self).__init__(*args, **kwargs)

    def to_dict(self):
        return {'pk' : self.pk,
                'participant_group_id': self.participant_group_relationship.pk,
                'participant_name': escape(self.participant_group_relationship.participant.full_name),
                'participant_number': self.participant_group_relationship.participant_number,
                'target': self.target_data_value,
                'date_created': timesince(self.date_created)
                }

class ActivityLog(models.Model):
    log_message = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
        return u"%s - %s" % (self.date_created.strftime("%m-%d-%Y %H:%M"), self.log_message)

class GroupActivityLog(ActivityLog):
    group = models.ForeignKey(Group, related_name='activity_log_set')
    round_configuration = models.ForeignKey(RoundConfiguration)

    def __unicode__(self):
        return u"%s %s" % (self.group, super(GroupActivityLog, self).__unicode__())

class ExperimentActivityLog(ActivityLog):
    experiment = models.ForeignKey(Experiment, related_name='activity_log_set')
    round_configuration = models.ForeignKey(RoundConfiguration)


def is_experimenter(user, experimenter=None):
    if hasattr(user, 'experimenter') and isinstance(user.experimenter, Experimenter):
        return True if experimenter is None else user.experimenter == experimenter
    return False

def is_participant(user):
    return hasattr(user, 'participant') and isinstance(user.participant, Participant)
