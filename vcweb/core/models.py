from datetime import datetime
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.core import mail, serializers
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.aggregates import Max
from django.db.models.loading import get_model
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.template import Context
from django.template.loader import select_template
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.managers import InheritanceManager, PassThroughManager
from string import Template
from social_auth.backends.facebook import FacebookBackend
import social_auth.signals

from vcweb.core import signals, simplecache, dumps

import base64
import hashlib
import logging
import random
import re
import string

logger = logging.getLogger(__name__)

"""
Contains all data models used in the core as well as a number of helper functions.
FIXME: getting a bit monolithically unwieldy.  Consider splitting into models subdirectory
"""

class DefaultValue(object):
    def __init__(self, value):
        self.value = value
    def __getattr__(self, name):
        return self.value

class AutoDateTimeField(models.DateTimeField):
    def pre_save(self, model_instance, add):
        return datetime.now()
from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^vcweb\.core\.models\.AutoDateTimeField"])

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
    short_name = models.SlugField(max_length=32, unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    about_url = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
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
    url = models.URLField(null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)

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

    @property
    def username(self):
        return self.user.username

    @property
    def is_active(self):
        return self.user.is_active

    def is_authenticated(self):
        return self.user.is_authenticated()

    def __unicode__(self):
        return u"%s (%s)" % (self.full_name, self.user.email)

    class Meta:
        abstract = True


class Experimenter(CommonsUser):
    approved = models.BooleanField(default=False)
    class Meta:
        ordering = ['user']

class ExperimenterRequest(models.Model):
    """
    a request for this user to be an experimenter, should notify admins
    """
    user = models.OneToOneField(User, verbose_name=u'Django User', unique=True)
    date_created = models.DateTimeField(default=datetime.now)
    approved = models.BooleanField(default=False)

class ExperimentConfiguration(models.Model):
    """
    The configuration for a given Experiment instance.  One ExperimentConfiguration can be applied to many Experiment
    instances but can only be associated to a single ExperimentMetadata record.
    """
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='experiment_configuration_set')
    creator = models.ForeignKey(Experimenter, related_name='experiment_configuration_set')
    name = models.CharField(max_length=255)
    max_number_of_participants = models.PositiveIntegerField(default=0)
    invitation_subject = models.TextField(null=True, blank=True, help_text=_('subject header for email registrations'))
    invitation_text = models.TextField(null=True, blank=True, help_text=_('text to send out via email invitations'))
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    is_public = models.BooleanField(default=False)
    max_group_size = models.PositiveIntegerField(default=5)
    exchange_rate = models.DecimalField(null=True, blank=True, max_digits=6, decimal_places=2, help_text=_('The exchange rate of currency per in-game token, e.g., dollars per token'))
    treatment_id = models.CharField(null=True, blank=True, max_length=32, help_text=_('An alphanumeric ID that should be unique to the set of ExperimentConfigurations for a given ExperimentMetadata'))
    is_experimenter_driven = models.BooleanField(default=True)
    """
    Experimenter driven experiments have checkpoints where the experimenter
    needs to explicitly signal the system to move to the next round or stage.
    """

    @property
    def is_open(self):
        '''
        using max_group_size of 0 to signify an open experiment, add a dedicated boolean field later if necessary
        '''
        return self.max_group_size == 0

    @is_open.setter
    def is_open(self, value):
        self.max_group_size = 0

    @property
    def final_sequence_number(self):
        # FIXME: or max round_configurations.sequence_number (as currently implemented could fail in the face of degenerate data)
        return self.round_configuration_set.count()

    @property
    def last_round_sequence_number(self):
        return self.round_configuration_set.aggregate(sequence_number=Max('sequence_number'))['sequence_number']

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    def get_parameter_value(self, parameter=None, name=None, default=None):
        if parameter is None and name is None:
            logger.error("Can't find a parameter value with no name or parameter, returning default")
            return default
        try:
            if parameter:
                return self.experiment_parameter_value_set.get(parameter=parameter)
            elif name:
                return self.experiment_parameter_value_set.get(parameter__name=name)
        except ExperimentParameterValue.DoesNotExist:
            logger.debug("no experiment configuration parameter value found: (%s, %s) returning default %s", parameter,
                    name, default)
            return DefaultValue(default)

    def serialize(self, output_format='xml', **kwargs):
        if self.round_configuration_set.count() > 0:
            all_objects = []
            for rc in self.round_configuration_set.all():
                all_objects.append(rc)
                all_objects.extend(rc.round_parameter_value_set.all())
            all_objects.append(self)
            return serializers.serialize(output_format, all_objects, **kwargs)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['experiment_metadata', 'creator', 'date_created']


class ExperimentQuerySet(models.query.QuerySet):
    def public(self, **kwargs):
        return self.filter(experiment_configuration__is_public=True, **kwargs)
    def active(self, **kwargs):
        return self.filter(status__in=('ACTIVE', 'ROUND_IN_PROGRESS'), **kwargs)
    def increment_elapsed_time(self, status='ROUND_IN_PROGRESS', amount=60):
        logger.debug("filtering on status %s", status)
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
    STATUS = Choices(
            ('INACTIVE', _('Not active')),
            ('ACTIVE', _('Active, no round in progress')),
            ('PAUSED', _('Paused')),
            ('ROUND_IN_PROGRESS', _('Round in progress')),
            ('COMPLETED', _('Completed')))
    (INACTIVE, ACTIVE, PAUSED, ROUND_IN_PROGRESS, COMPLETED) = [ choice[0] for choice in STATUS ]
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
# FIXME: consider using django-model-utils but need to verify that it works with South
# status = StatusField()
    status = models.CharField(max_length=32, choices=STATUS, default=STATUS.INACTIVE)
    """
    the status of an experiment can be either INACTIVE, ACTIVE, PAUSED, ROUND_IN_PROGRESS, or COMPLETED
    """
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
# FIXME: inherit from TimeFramedModel instead?
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
    amqp_exchange_name = models.CharField(max_length=64, default="vcweb.default.exchange")

    ready_participants = models.PositiveIntegerField(default=0, help_text=_("The number of participants ready to move on to the next round."))

    cached_round_sequence_number = None
    ''' used to cache the round configuration '''

    objects = PassThroughManager.for_queryset_class(ExperimentQuerySet)()

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
    def status_label(self):
        return u"%s, %s" % (self.get_status_display(), self.current_round.get_round_type_display())
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
        '''
        Generator function for all participant group relationships in this experiment
        '''
        session_id = self.current_round.session_id
        if session_id is not None:
            groups = self.group_set.filter(session_id=session_id)
        else:
            groups = self.group_set.all()
        for group in groups:
            for pgr in group.participant_group_relationship_set.all():
                yield pgr

    @property
    def display_name(self):
        return self.experiment_metadata.title

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

    @property
    def participant_emails(self):
        return self.participant_set.all().values_list('user__email', flat=True)

    def get_absolute_url(self):
        return "%s/%s" % (self.experiment_metadata.namespace, self.pk)

    @property
    def current_round_template(self):
        return self.current_round.template_path

    @property
    def current_round(self):
        csn = self.cached_round_sequence_number
        if csn is None or self.current_round_sequence_number != self.cached_round_sequence_number:
            self.cached_round_sequence_number = self.current_round_sequence_number
            self.cached_round = self.get_round_configuration(self.current_round_sequence_number)
        return self.cached_round

    @property
    def current_round_data(self):
        return self.get_round_data(round_configuration=self.current_round)

# FIXME: cache this as well to avoid a query per invocation
    def get_round_data(self, round_configuration=None):
        if round_configuration is None:
            round_configuration = self.current_round
        return RoundData.objects.select_related('round_configuration').get(experiment=self, round_configuration=round_configuration)

    @property
    def playable_round_data(self):
        return self.round_data_set.select_related(depth=1).filter(round_configuration__round_type__in=RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS,
                round_configuration__sequence_number__lte=self.current_round_sequence_number)

    @property
    def all_chat_messages(self):
        return ChatMessage.objects.filter(round_data__experiment=self)

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
    def is_public(self):
        return self.experiment_configuration.is_public

    @property
    def actions_help_text(self):
        if hasattr(self, 'custom_help_text'):
            return self.custom_help_text['actions']
        # return dynamic text based on current_round?
        return self.current_round.instructions

    @property
    def all_participants_ready(self):
        return self.ready_participants >= self.participant_set.count()

    def get_participant_group_relationship(self, participant):
        session_id = self.current_round.session_id
        if session_id is None:
            return ParticipantGroupRelationship.objects.get(group__experiment=self, participant=participant)
        else:
            return ParticipantGroupRelationship.objects.get(group__experiment=self, participant=participant,
                    group__session_id=session_id)

    def all_participants_have_submitted(self):
        return ParticipantRoundDataValue.objects.filter(submitted=False, round_data=self.current_round_data).count() == 0

    def register_participants(self, users=None, emails=None, institution=None, password=None):
        if self.participant_set.count() > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, self.participant_set.count())
            return
        if users is None:
            users = []
            if emails is None:
                logger.warning("No users or emails supplied, aborting.")
                return
            for email in emails:
                if not email:
                    logger.debug("invalid participant data: %s", email)
                    continue
                # FIXME: push this logic into the form clean / EmailListField.clean instead?
                # XXX: handle incoming firstname lastname email data
                data = email.split()
                first_name = None
                last_name = None
                if len(data) >= 3:
                    email = data.pop()
                    last_name = data.pop()
                    first_name = ' '.join(data)
# convert all usernames/email addresses to lowercase internally and strip any whitespace
                email = email.lower().strip()
                try:
                    u = User.objects.get(username=email)
                except User.DoesNotExist:
                    u = User.objects.create_user(username=email, email=email, password=password)
                    if first_name and last_name:
                        logger.debug("setting first name [%s] and last name [%s]", first_name, last_name)
                        u.first_name = first_name
                        u.last_name = last_name
                        u.save()
                users.append(u)
        email_messages = []
        for user in users:
            # FIXME: unsafe for concurrent usage, but only one experimenter at a time should be invoking this
            (p, created) = Participant.objects.get_or_create(user=user)
            # FIXME: instead of asking for the email suffix, perhaps we just append the institution URL to keep it simpler?
            if institution and p.institution != institution:
                p.institution = institution
                p.save()
            per = ParticipantExperimentRelationship.objects.create(participant=p, experiment=self, created_by=self.experimenter.user)
            email_messages.append(self.create_registration_email(per, password=password))
        if email_messages:
            mail.get_connection().send_messages(email_messages)

    def create_registration_email(self, participant_experiment_relationship, password=None, **kwargs):
        '''
        Override the email template by creating <experiment-namespace>/email/experiment-registration(txt|html) template files
        '''
        logger.debug("sending email to %s", participant_experiment_relationship.participant)
        plaintext_template = select_template(['%s/email/experiment-registration.txt' % self.namespace, 'email/experiment-registration.txt'])
        html_template = select_template(['%s/email/experiment-registration.html' % self.namespace, 'email/experiment-registration.html'])
        experiment = participant_experiment_relationship.experiment
        participant = participant_experiment_relationship.participant
        user = participant.user
        if password is None:
            password = User.objects.make_random_password()
# FIXME: this resets existing user passwords..
        user.set_password(password)
        user.save()
        c = Context({
            'participant_experiment_relationship': participant_experiment_relationship,
            'participant': participant,
            'experiment': experiment,
            'password': password,
            })
        plaintext_content = plaintext_template.render(c)
        html_content = html_template.render(c)
        subject = self.experiment_configuration.invitation_subject
        if subject is None:
            subject = 'VCWEB: experiment registration for %s' % self.display_name
        experimenter_email = self.experimenter.email
        to_address = [ participant_experiment_relationship.participant.email, experimenter_email ]
        msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address)
        msg.attach_alternative(html_content, "text/html")
        return msg

    ''' FIXME: get rid of hardcoded defaults for the slovakia pretest '''
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
        self.register_participants(users=users, institution=institution, password=password)

    def initialize_data_values(self, group_parameters=None, participant_parameters=None, round_data=None):
        logger.debug("initializing [participant params: %s]  [group parameters: %s] ", participant_parameters, group_parameters)
        if group_parameters is None:
            group_parameters = self.parameters(scope=Parameter.GROUP_SCOPE)
        if participant_parameters is None:
            participant_parameters = self.parameters(scope=Parameter.PARTICIPANT_SCOPE)
        if round_data is None:
            round_data = self.current_round_data
        for group in self.group_set.select_related('parameter').all():
            for parameter in group_parameters:
                group_data_value, created = GroupRoundDataValue.objects.get_or_create(round_data=round_data, group=group, parameter=parameter)
        #        logger.debug("%s (%s)", group_data_value, created)
            if participant_parameters:
                for pgr in group.participant_group_relationship_set.all():
                    for parameter in participant_parameters:
                        participant_data_value, created = ParticipantRoundDataValue.objects.get_or_create(round_data=round_data, participant_group_relationship=pgr, parameter=parameter)
        #                logger.debug("%s (%s)", participant_data_value, created)

    def log(self, log_message):
        if log_message:
            logger.debug("%s: %s", self, log_message)
            self.activity_log_set.create(round_configuration=self.current_round, log_message=log_message)

    def configuration_file_name(self, file_ext='.xml'):
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        return '%s_experiment-configuration_%s%s' % (slugify(self.display_name), self.pk, file_ext)

    def data_file_name(self, file_ext='.csv'):
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        return "%s_%s_%s%s" % (slugify(self.experiment_metadata.title), self.pk, datetime.now().strftime("%m-%d-%Y-%H%M"), file_ext)

    def parameters(self, scope=None):
        parameter_set = self.experiment_metadata.parameter_set
        return parameter_set.filter(scope=scope) if scope else parameter_set

    def add_participant(self, participant, current_group=None):
        # FIXME: simplify logic where possible
        if participant not in self.participant_set.all():
            logger.warning("participant %s not a member of this experiment %s, adding them", participant, self)
            ParticipantExperimentRelationship.objects.create(participant=participant, experiment=self,
                    created_by=participant.user)
        pgrs = ParticipantGroupRelationship.objects.filter(group__experiment=self, participant=participant)
        # FIXME: full strictness should be pgrs.count() == 0
        if pgrs.count() > 0:
            # return this ParticipantGroupRelationship if this participant is already a member of a group in this experiment.
            return pgrs.all()[0]

        if current_group is None:
            if self.group_set.count() == 0:
                # create a new group
                current_group = self.group_set.create(number=1, max_size=self.experiment_configuration.max_group_size)
            else:
                # pick the last group in group_set
                current_group = self.group_set.reverse()[0]
        return current_group.add_participant(participant)

    def allocate_groups(self, randomize=True):
        logger.debug("allocating groups for %s (randomize? %s)" % (self, randomize))
        # clear out all existing groups
        # FIXME: record previous mappings in activity log.
        gs = self.group_set
        if gs.count() > 0:
            self.log("reallocating groups, deleting old groups")
            gqs = gs.all()
            for g in gqs:
                self.log("reallocating group %s" % g.participant_group_relationship_set.all())
            gqs.delete()
        # seed the initial group.
        max_group_size = self.experiment_configuration.max_group_size
        logger.debug("creating group with max size %d", max_group_size)
        current_group = self.group_set.create(number=1, max_size=max_group_size)
        participants = list(self.participant_set.all())
        if randomize:
            random.shuffle(participants)
        for p in participants:
            pgr = self.add_participant(p, current_group)
            current_group = pgr.group

    def get_round_configuration(self, sequence_number):
        return RoundConfiguration.objects.get(experiment_configuration__experiment=self, sequence_number=sequence_number)

    def get_template_path(self, name):
        return "%s/%s" % (self.namespace, name)

    # XXX: decide whether or not to include this ability in the interface.
    def move_to_previous_round(self):
        if self.is_round_in_progress:
            self.end_round()
        self.current_round_elased_time = 0
        self.current_round_sequence_number = max(self.current_round_sequence_number - 1, 1)
        self.save()

    def invoke(self, action_name):
        if action_name in ('advance_to_next_round', 'end_round', 'start_round', 'activate', 'complete'):
            getattr(self, action_name)()
        else:
            raise AttributeError("Invalid experiment action %s requested of experiment %s" % (action_name, self))

    def advance_to_next_round(self):
        if self.is_round_in_progress:
            self.end_round()
        if self.has_next_round:
            self.current_round_elapsed_time = 0
            self.current_round_sequence_number += 1
            self.start_round()
        else:
            logger.warning("trying to advance past the last round - no-op")

    def create_round_data(self):
        round_data, created = self.round_data_set.get_or_create(round_configuration=self.current_round)
        if self.experiment_configuration.is_experimenter_driven:
            # create participant ready data values for every round in experimenter driven experiments
            for pgr in self.participant_group_relationships:
                ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr, boolean_value=False,
                        parameter=get_participant_ready_parameter(), round_data=round_data)
        if not created:
            logger.debug("already created round data: %s", round_data)
        return round_data

    def start_round(self, sender=None):
        logger.debug("%s STARTING ROUND (sender: %s)", self, sender)
        self.status = 'ROUND_IN_PROGRESS'
        self.create_round_data()
        self.current_round_elapsed_time = 0
        self.current_round_start_time = datetime.now()
        self.ready_participants = 0
        self.save()
        self.log('Starting round')
        # FIXME: would prefer using self.namespace as a default but django's
        # managed unicode strings don't work as senders
        sender = intern(self.experiment_metadata.namespace.encode('utf8')) if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        # notify registered game handlers
        logger.debug("About to send round started signal with sender %s", sender)
        return signals.round_started.send_robust(sender, experiment=self, time=datetime.now(), round_configuration=self.current_round)

    def end_round(self, sender=None):
        self.status = 'ACTIVE'
        self.current_round_elapsed_time = max(self.current_round_elapsed_time, self.current_round.duration)
        self.save()
        self.log('Ending round with elapsed time %s' % self.current_round_elapsed_time)
        sender = intern(self.experiment_metadata.namespace.encode('utf8')) if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        logger.debug("about to send round ended signal with sender %s", sender)
        return signals.round_ended.send_robust(sender, experiment=self, round_configuration=self.current_round)

    def activate(self):
        if not self.is_active:
            self.allocate_groups()
            self.status = 'ACTIVE'
            self.start_date_time = datetime.now()
            self.save()
        return self

    def complete(self):
        self.log("Marking as COMPLETED") 
        self.status = 'COMPLETED'
        self.save()

    def stop(self):
        self.log("Stopping experiment and flagging as inactive.")
        self.status = 'INACTIVE'
        self.save()

    def check_elapsed_time(self):
        if self.is_timed_round and self.is_time_expired:
            self.end_round()

# FIXME: figure out a better way to convert these to json that doesn't involve manual remapping of attribute names...
# or be consistent so that things on the client side are named the same as the server side
    def all_round_data(self):
        all_round_data = []
        for round_data in self.round_data_set.reverse():
            group_data_values = [gdv.to_dict() for gdv in round_data.group_data_value_set.select_related('group', 'parameter').all()]
            participant_data_values = [pdv.to_dict(include_email=True, cacheable=True) for pdv in round_data.participant_data_value_set.select_related('participant_group_relationship__participant__user', 'parameter').all()]
            rc = round_data.round_configuration
            all_round_data.append({
                'roundDataId': "roundData_%s" % round_data.pk,
                'roundType': rc.get_round_type_display(),
                'roundNumber':rc.round_number,
                'groupDataValues': group_data_values,
                'participantDataValues': participant_data_values
                })
        return all_round_data

    def to_dict(self, include_round_data=True, *args, **kwargs):
        ec = self.experiment_configuration
        experiment_dict = {
                'roundStatusLabel': self.status_label,
                'roundSequenceLabel': self.sequence_label,
                'timeRemaining': self.time_remaining,
                'currentRoundStartTime': self.current_round_start_time.strftime('%c') if self.current_round_start_time else 'N/A',
                'participantCount': self.participant_set.count(),
                'isRoundInProgress': self.is_round_in_progress,
                'isActive': self.is_active,
                'dollarsPerToken': float(ec.exchange_rate),
                }
        if include_round_data:
            experiment_dict['allRoundData'] = self.all_round_data()
            experiment_dict['chatMessages'] = [chat_message.to_dict() for chat_message in self.all_chat_messages]
            experiment_dict['messages'] = [escape(log) for log in self.activity_log_set.order_by('-date_created')]
        return experiment_dict

    def as_dict(self, *args, **kwargs):
        return self.to_dict(*args, **kwargs)

    def to_json(self, include_round_data=True, *args, **kwargs):
        return dumps(self.as_dict(include_round_data, *args, **kwargs))

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
    ROUND_TYPES_DICT = dict(
            WELCOME=('Initial welcome round', 'welcome.html'),
            REGULAR=('Regular experiment round', 'participate.html'),
            CHAT=('Chat round', 'chat.html'),
            DEBRIEFING=('Debriefing round', 'debriefing.html'),
            INSTRUCTIONS=('Instructions round', 'instructions.html'),
            PRACTICE=('Practice round', 'practice.html'),
            QUIZ=('Quiz round', 'quiz.html'))
    ROUND_TYPES = (CHAT, DEBRIEFING, INSTRUCTIONS, PRACTICE, QUIZ, REGULAR, WELCOME) = sorted(ROUND_TYPES_DICT.keys())

    ROUND_TYPE_CHOICES = [(round_type, ROUND_TYPES_DICT[round_type][0]) for round_type in ROUND_TYPES]
    PLAYABLE_ROUND_CONFIGURATIONS = (PRACTICE, REGULAR)

    experiment_configuration = models.ForeignKey(ExperimentConfiguration, related_name='round_configuration_set')
    sequence_number = models.PositiveIntegerField(help_text='Used internally to determine the ordering of the rounds in an experiment in ascending order, e.g., 1,2,3,4,5')
    display_number = models.PositiveIntegerField(default=0,
                                               help_text='The round number to be displayed with this round.  If set to zero, defaults to the internally used sequence_number.')
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    duration = models.PositiveIntegerField(default=0,
                                           help_text='Duration in seconds.  0 means an untimed round that can only be advanced by an experimenter.')
    """
    How long should this round execute before advancing to the next?
    Interpreted as whole seconds.
    """
    instructions = models.TextField(null=True, blank=True)
    """ instructions, if any, to display before the round begins """
    debriefing = models.TextField(null=True, blank=True)
    """ debriefing, if any, to display after the round ends """
# FIXME: replace with model_utils Choices
    round_type = models.CharField(max_length=32,
                                  choices=ROUND_TYPE_CHOICES,
                                  default=REGULAR)
    """
    name of a custom template to be used this round.  e.g., if set to
    quiz_2.html in the forestry experiment app, this would be loaded from
    forestry/templates/forestry/quiz_2.html
    """
    template_name = models.CharField(max_length=64, null=True, blank=True,
            help_text=_('''The name of the template to use to render when executing this round.
                        This file should exist in your templates directory as your-experiment-namespace/template-name.html,
                        e.g., if set to foo.html, vcweb will look for templates/forestry/foo.html'''))
    survey_url = models.URLField(null=True, blank=True)
    """ external survey url """
    randomize_groups = models.BooleanField(default=False, help_text=_("Shuffle participants into new groups when the round begins?"))
    """ Should groups be randomized at the start of the round? """
    preserve_existing_groups = models.BooleanField(default=True, help_text=_("This option is only useful if randomize_groups is set to true.  If we are randomizing groups, should existing groups (if any) be preserved?"))
    """ Should existing groups (if any) be preserved? """
    session_id = models.CharField(max_length=64, null=True, blank=True,
            help_text=_('''
            Session id to associate with this round data and the groups in this experiment, useful for longer
            multi-session experiments where group membership may change.  We don't want to destroy the old groups as
            that information is still needed to determine payments, etc. Instead we need to create a new set of
            Group/ParticipantGroupRelationship models that can live in conjunction with the existing
            Group/ParticipantGroupRelationship models.
            '''))

    @property
    def custom_template_name(self):
        return self.template_name if self.template_name else self.default_template_name

    @property
    def default_template_name(self):
        return RoundConfiguration.ROUND_TYPES_DICT[self.round_type][1]

    def get_custom_instructions(self, context_dict=None, **kwargs):
        if not self.is_instructions_round:
            logger.warning("tried to get custom instructions for a non-instructions round %s", self)
            return None
        instructions_template = select_template([self.template_path])
        if context_dict is None:
            context_dict = {}
        context_dict.update(kwargs)
        c = Context(context_dict)
        return instructions_template.render(c)

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

    def get_parameter_value(self, parameter=None, name=None, default=None):
        if parameter is None and name is None:
            logger.error("Can't find a parameter value with no name or parameter, returning default")
            return default
        try:
            if parameter:
                return RoundParameterValue.objects.get(round_configuration=self, parameter=parameter)
            elif name:
                return RoundParameterValue.objects.get(round_configuration=self, parameter__name=name)
        except RoundParameterValue.DoesNotExist:
            return DefaultValue(default)

    def is_survey_enabled(self):
        try:
            return self.survey_url is not None
        except:
            return False

    def get_debriefing(self, participant_id=None, **kwargs):
        return self.templatize(self.debriefing, participant_id, kwargs)

    def get_instructions(self, participant_id=None, **kwargs):
        return self.templatize(self.instructions, participant_id, kwargs)


    def templatize(self, template_string, participant_id=None, **kwargs):
        return Template(template_string).substitute(kwargs, round_number=self.display_number, participant_id=participant_id)

    def __unicode__(self):
        return u"%s %s (%s)" % (self.get_round_type_display(), self.sequence_label, self.experiment_configuration)

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

def _fk_converter(fk_cls):
    def converter(value):
        if isinstance(value, (int, long)):
            return value
        elif isinstance(value, fk_cls):
            return value.pk
        raise ValueError("can only convert integers or %s - received %s" % (fk_cls, value))
    return converter


class ParameterQuerySet(models.query.QuerySet):
    def for_participant(self, **kwargs):
        return self.get(scope=Parameter.PARTICIPANT_SCOPE, **kwargs)

    def for_group(self, **kwargs):
        return self.get(scope=Parameter.GROUP_SCOPE, **kwargs)

    def for_group_round(self, **kwargs):
        return self.get(scope=Parameter.GROUP_ROUND_SCOPE, **kwargs)

    def for_round(self, **kwargs):
        return self.get(scope=Parameter.ROUND_SCOPE, **kwargs)

    def for_experiment(self, **kwargs):
        return self.get(scope=Parameter.EXPERIMENT_SCOPE, **kwargs)

class ParameterPassThroughManager(PassThroughManager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Parameter(models.Model):
    PARAMETER_TYPES = (('int', 'Integer'),
                       ('string', 'String'),
                       ('foreignkey', 'Foreign key'),
                       ('float', 'Floating-point number'),
                       ('boolean', (('True', True), ('False', False))),
                       ('enum', 'Enumeration'))

    # FIXME: arcane, see if we can encapsulate this better.  used to provide sane default values for each parameter type
    # when the parameter is null
    NONE_VALUES_DICT = dict(map(lambda x,y: (x[0], y), PARAMETER_TYPES, [0, '', -1, 0.0, False, None]))
    #dict(zip([parameter_type[0] for parameter_type in PARAMETER_TYPES], [0, '', 0.0, False, None]))

    CONVERTERS = {
            'int': int,
            'string':str,
            'float': float,
            'foreignkey': _fk_converter,
            'boolean': lambda x: bool(x) and str(x).lower() != 'false',
            'enum': str,
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
    class_name = models.CharField(max_length=64, null=True, blank=True, help_text='Model classname in the form of appname.modelname, e.g., "core.Experiment".  Only applicable for foreign key parameters.')
    default_value_string = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    creator = models.ForeignKey(Experimenter)
    experiment_metadata = models.ForeignKey(ExperimentMetadata, null=True, blank=True)
    enum_choices = models.TextField(null=True, blank=True)
    is_required = models.BooleanField(default=False)

    objects = ParameterPassThroughManager.for_queryset_class(ParameterQuerySet)()

    @property
    def value_field_name(self):
        t = self.type
        if t == 'foreignkey':
            return 'int_value'
        elif t == 'enum':
            return 'string_value'
        return '%s_value' % (t)

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

    @property
    def is_integer_type(self):
        return self.type == 'int' or self.type == 'foreignkey'

    @property
    def is_boolean_type(self):
        return self.type == 'boolean'

    @property
    def is_float_type(self):
        return self.type == 'float'

    @property
    def is_string_type(self):
        return self.type == 'string'

    @property
    def is_foreign_key(self):
        return self.type == 'foreignkey'

    def lookup(self, pk=None):
        return self.get_model_class().objects.get(pk=pk)

    def get_model_class(self):
        return get_model(*self.class_name.split('.'))

    def get_converter(self):
        converter = Parameter.CONVERTERS[self.type]
        # FIXME: hacky special case curried converter for fk lookups that stores an int given a model instance or pk
        return converter(self.get_model_class()) if self.type == 'foreignkey' else converter

    def convert(self, value=None):
        converter = self.get_converter()
        try:
            return converter(value) if converter else value
        except ValueError:
            if self.is_integer_type:
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
    date_created = models.DateTimeField(default=datetime.now, db_index=True)
    last_modified = AutoDateTimeField(default=datetime.now)
    is_active = models.BooleanField(default=True)

    @property
    def cache_key(self):
        p = self.parameter
        if p.is_foreign_key:
            return "%s-%s" % (p.name, self.int_value)
        else:
            return "%s-%s" % (p.name, self.pk)

    @property
    def cached_value(self):
        ck = self.cache_key
        cv = cache.get(ck)
        if cv is None:
            cv = self.value
            cache.set(ck, cv)
        return cv

    @property
    def value(self):
        value = getattr(self, self.parameter.value_field_name, self.parameter.none_value)
        if value is None:
            return self.parameter.none_value
        if self.parameter.is_foreign_key:
            return self.parameter.lookup(pk=value)
        else:
            return value

    @value.setter
    def value(self, obj):
        converted_value = self.parameter.convert(obj)
        setattr(self, self.parameter.value_field_name, converted_value)

    def to_dict(self, cacheable=False, **kwargs):
        p = self.parameter
        data = {'pk' : self.pk,
                'date_created': self.date_created,
                'short_date_created': self.date_created.strftime('%I:%M:%S'),
                'parameter_name': p.name,
                'parameter_label': p.label,
                'parameter': self.parameter
                }
        data['value'] = unicode(self.cached_value if cacheable else self.value)
        return data

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2}".format(self.parameter, self.value, self.date_created)

    class Meta:
        abstract = True

# configuration parameters across the entire experiment
class ExperimentParameterValue(ParameterizedValue):
    experiment_configuration = models.ForeignKey(ExperimentConfiguration, related_name='experiment_parameter_value_set')

    def __unicode__(self):
        ec = self.experiment_configuration
        return u"{0} -> [{1}: {2}]".format(ec, self.parameter, self.value)

class RoundParameterValue(ParameterizedValue):
    """
    Represents a specific piece of round configuration data.
    """
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_parameter_value_set')

    def __unicode__(self):
        rc = self.round_configuration
        return u"{0}:{1} -> [{2}: {3}]".format(rc.experiment_configuration, rc.sequence_label, self.parameter, self.value)

class Group(models.Model):
    number = models.PositiveIntegerField()
    ''' internal numbering unique to the given experiment '''
    max_size = models.PositiveIntegerField(default=5)
    """
    how many members can this group hold at a maximum?
    """
    experiment = models.ForeignKey(Experiment)
    """
    The experiment that contains this Group.
    """
    session_id = models.CharField(max_length=64, null=True, blank=True)

    @property
    def name(self):
        return u"Group %s" % string.ascii_uppercase[max(self.number - 1, 0)]

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
        return self.experiment.get_round_data(round_configuration=self.current_round)

    def get_round_data(self, round_configuration=None):
        return self.experiment.get_round_data(round_configuration)

    @property
    def is_full(self):
        return self.size >= self.max_size > 0

    @property
    def is_open(self):
        return not self.is_full

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
        updated_rows = self.data_value_set.filter(round_data=self.current_round_data, parameter=parameter).update(**update_dict)
        if updated_rows != 1:
            logger.error("Updated %s rows, should have been only one.", updated_rows)

    def has_data_parameter(self, **kwargs):
        criteria = self._data_parameter_criteria(**kwargs)
        try:
            return self.data_value_set.filter(**criteria).count() > 0
        except:
            return False

    def get_scalar_data_value(self, parameter=None, **kwargs):
        return self.get_data_value(parameter=parameter, **kwargs).value

    def get_round_configuration_value(self, parameter=None, name=None, current_round_configuration=None, **kwargs):
        if current_round_configuration is None:
            current_round_configuration = self.current_round
        round_configuration_value = None
        try:
            if parameter is not None:
                round_configuration_value = RoundParameterValue.objects.get(parameter=parameter, round_configuration=current_round_configuration)
            elif name is not None:
                round_configuration_value = RoundParameterValue.objects.get(parameter__name=name, round_configuration=current_round_configuration)
            else:
                logger.warn("No parameter or parameter name specified: %s", **kwargs)
        except:
            logger.debug("no round configuration value found for parameter (%s, %s) in round: %s", parameter, name, current_round_configuration)
        return round_configuration_value

    def get_data_value(self, parameter=None, parameter_name=None, round_data=None, default=None):
        ''' returns a tuple of (scalar data value, entity DataValue).  if no entity data value exists, returns (default value, None) '''
        if round_data is None:
            round_data = self.current_round_data
        criteria = self._data_parameter_criteria(parameter=parameter, parameter_name=parameter_name, round_data=round_data)
        try:
            return self.data_value_set.select_related('parameter', 'group', 'round_data').get(**criteria)
        except GroupRoundDataValue.DoesNotExist as e:
            if default is None:
                raise e
            else:
                return DefaultValue(default)

    def set_data_value(self, parameter=None, value=None, round_data=None, **kwargs):
        '''
        Not as efficient as a simple SQL update because we need to do some type
        conversion / processing to put the value into the appropriate field.
        '''
        if round_data is None:
            round_data = self.current_round_data
        self.log("setting group param %s => %s" % (parameter, value))
        grdv = GroupRoundDataValue.objects.get(parameter=parameter, round_data=round_data, group=self)
        grdv.value = value
        grdv.save()
        return grdv

    def _data_parameter_criteria(self, parameter=None, parameter_name=None, round_data=None, **kwargs):
        criteria = dict([
            ('parameter__pk', parameter.pk) if parameter else ('parameter__name', parameter_name),
            ('round_data__pk', self.current_round_data.pk if round_data is None else round_data.pk)
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

    def copy_to_next_round(self, data_value):
        ''' copies the given data value to the next round if it exists and returns the newly created group data value'''
        return self.transfer_parameter(data_value.parameter, data_value.value)

    def transfer_parameter(self, parameter, value):
        e = self.experiment
        if e.is_last_round:
            logger.error("Trying to transfer parameter (%s: %s) past the last round of the experiment",
                    parameter, value)
            return None
        next_round_data, created = RoundData.objects.get_or_create(experiment=e, round_configuration=e.next_round)
        logger.debug("next round data: %s (%s)", next_round_data, created)
        gdv, created = GroupRoundDataValue.objects.get_or_create(group=self, round_data=next_round_data, parameter=parameter)
        logger.debug("group data value: %s (%s)", gdv, created)
        gdv.value = value
        gdv.save()
        return gdv

    def get_participant_data_values(self, **kwargs):
        criteria = self._data_parameter_criteria(participant_group_relationship__group=self, **kwargs)
        return ParticipantRoundDataValue.objects.filter(**criteria)

    def create_next_group(self):
        return Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment)

    """
    Adds the given participant to this group or a new group if this group is is_full.
    Returns the participant group relationship created by adding this participant or None if the participant is invalid.
    """
    def add_participant(self, participant=None):
        if participant is None:
            logger.warning("Trying to add invalid participant %s to group %s", participant, self)
            return None

        ''' add the participant to this group if there is room, otherwise create and add to a fresh group '''
        group = self if self.is_open else self.create_next_group()
        pgr = ParticipantGroupRelationship.objects.create(participant=participant,
                group=group,
                round_joined=self.experiment.current_round,
                participant_number=group.size + 1)
        signals.participant_added.send_robust(self, experiment=self.experiment, time=datetime.now(), participant_group_relationship=pgr)
        return pgr

    def __unicode__(self):
        return u"Group #{0}".format(self.number)

    class Meta:
        ordering = ['experiment', 'number']

class GroupCluster(models.Model):
    date_created = models.DateTimeField(default=datetime.now)
    name = models.CharField(max_length=64, null=True, blank=True)
    session_id = models.CharField(max_length=64, null=True, blank=True)
    experiment = models.ForeignKey(Experiment)

    def __unicode__(self):
        return u"group cluster %s (%s)" % (self.name, self.experiment)

    class Meta:
        ordering = ['date_created']

class GroupRelationship(models.Model):
    date_created = models.DateTimeField(default=datetime.now)
    cluster = models.ForeignKey(GroupCluster, related_name='group_set')
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return u"group %s in cluster %s" % (self.group, self.cluster)

    class Meta:
        ordering = ['date_created']

class RoundData(models.Model):
    """
    round-specific data for a given experiment.  Contains related sets to group_data
    (GroupRoundDataValue), participant_data (ParticipantRoundDataValue), and
    chat_messages (ChatMessage)
    """
    experiment = models.ForeignKey(Experiment, related_name='round_data_set')
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='round_data_set')
    elapsed_time = models.PositiveIntegerField(default=0)
    experimenter_notes = models.TextField(null=True, blank=True)

    @property
    def session_id(self):
        return self.round_configuration.session_id

    def __unicode__(self):
        return u"Data for Round %s (%s)" % (self.round_configuration.sequence_number, self.round_configuration.get_round_type_display())

    class Meta:
        ordering = [ 'round_configuration' ]
        unique_together = (('round_configuration', 'experiment'),)

class GroupClusterDataValue(ParameterizedValue):
    group_cluster = models.ForeignKey(GroupCluster)
    round_data = models.ForeignKey(RoundData, related_name='group_cluster_data_value_set')

class GroupRoundDataValue(ParameterizedValue):
    group = models.ForeignKey(Group, related_name='data_value_set')
    round_data = models.ForeignKey(RoundData, related_name='group_data_value_set')

    def to_dict(self, **kwargs):
        data = super(GroupRoundDataValue, self).to_dict(**kwargs)
        data.update({
            'group': self.group.name,
            })
        return data

    @property
    def owner(self):
        return self.group

    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def __unicode__(self):
        return u"{0}={1} ({2}, {3})".format(self.parameter, self.value, self.group, self.round_configuration)

    class Meta:
        ordering = [ 'round_data', 'group', 'parameter' ]


class Address(models.Model):
    street1 = models.CharField(_('Street'), max_length=256)
    street2 = models.CharField(_('Street'), max_length=256)
    city = models.CharField(_('City'), max_length=128, blank=True)
    state = models.CharField(_('State'), max_length=128, blank=True)
    zipcode = models.CharField(_('Zip code'), max_length=8, blank=True)

class Participant(CommonsUser):
    GENDER_CHOICES = (('M', 'Male'), ('F', 'Female'),)
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participant_set')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participant_set')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    address = models.ForeignKey(Address, null=True, blank=True)

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
        return ParticipantGroupRelationship.objects.get_relationship(self, experiment)

    def experiments_with_status(self, status=Experiment.ACTIVE):
        return self.experiment_relationship_set.filter(experiment__status=status)

    class Meta:
        ordering = ['user']


class ParticipantExperimentRelationshipQuerySet(models.query.QuerySet):
    def active(self, **kwargs):
        return self.filter(experiment__status__in=('ACTIVE', 'ROUND_IN_PROGRESS'), **kwargs)

class ParticipantExperimentRelationship(models.Model):
    """
    Many-to-many relationship entity storing a participant and the experiment they are participating in.
    """
    participant = models.ForeignKey(Participant, related_name='experiment_relationship_set')
    participant_identifier = models.CharField(max_length=32)
    sequential_participant_identifier = models.PositiveIntegerField()
    experiment = models.ForeignKey(Experiment, related_name='participant_relationship_set')
    date_created = models.DateTimeField(default=datetime.now)
    created_by = models.ForeignKey(User)
    last_completed_round_sequence_number = models.PositiveIntegerField(default=0)
    current_location = models.CharField(max_length=64, null=True, blank=True)
# arbitrary JSON-encoded data
    additional_data = models.TextField(null=True, blank=True)

    objects = PassThroughManager.for_queryset_class(ParticipantExperimentRelationshipQuerySet)()

    def __init__(self, *args, **kwargs):
        super(ParticipantExperimentRelationship, self).__init__(*args, **kwargs)
        if 'experiment' in kwargs:
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

class ParticipantGroupRelationshipQuerySet(models.query.QuerySet):

    def for_experiment(self, experiment):
        return self.select_related('group', 'participant').filter(group__experiment=experiment)

# FIXME: deprecated, for backwards compatibility
    def by_experiment(self, experiment):
        return self.for_experiment(experiment)

    def get_relationship(self, participant, experiment):
        try:
            return self.select_related('group', 'participant__user').get(group__experiment=experiment, participant=participant)
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
    date_created = models.DateTimeField(default=datetime.now)
    active = models.BooleanField(default=True)
    first_visit = models.BooleanField(default=True)
    notifications_since = models.DateTimeField(default=datetime.now, null=True, blank=True)

    objects = PassThroughManager.for_queryset_class(ParticipantGroupRelationshipQuerySet)()

    @property
    def current_round_data(self):
        return self.group.current_round_data

    def get_round_data(self, round_configuration=None):
        return self.group.get_round_data(round_configuration)

    @property
    def full_name(self):
        fn = self.participant.user.get_full_name()
        if not fn:
            fn = self.participant_handle
        return fn

    @property
    def participant_handle(self):
        return "Participant %s" % self.participant_number

    @property
    def experiment(self):
        return self.group.experiment

    @property
    def group_number(self):
        return self.group.number

    def get_round_configuration_value(self, **kwargs):
        return self.group.get_round_configuration_value(**kwargs)

    def get_data_value(self, parameter=None, round_data=None, default=None):
        if round_data is None:
            round_data = self.current_round_data
        if parameter is not None:
            return ParticipantRoundDataValue.objects.get(round_data=round_data, parameter=parameter,
                    participant_group_relationship=self)
        logger.warning("unable to retrieve data value with parameter %s, returning default value %s", parameter, default)
        return DefaultValue(default)

    def set_data_value(self, parameter=None, value=None, round_data=None):
        if round_data is None:
            round_data = self.current_round_data
        if parameter is not None and value is not None:
            pdv = ParticipantRoundDataValue.objects.get(round_data=round_data, parameter=parameter, participant_group_relationship=self)
            pdv.submitted = True
            pdv.value = value
            pdv.save()
            # FIXME: parameterize / make explicit?
            return pdv
        else:
            logger.warning("Unable to set data value %s on round data %s for %s", value, round_data, parameter)

    def __unicode__(self):
        return u"{0}: #{1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['group', 'participant_number']

class ParticipantRoundDataValueQuerySet(models.query.QuerySet):
    def for_group(self, group=None, **kwargs):
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                'target_data_value__participant_group_relationship',
                ).filter(participant_group_relationship__group=group, **kwargs).order_by('-date_created')

class ParticipantRoundDataValue(ParameterizedValue):
    def __init__(self, *args, **kwargs):
        if 'round_data' not in kwargs and 'participant_group_relationship' in kwargs:
            kwargs['round_data'] = kwargs['participant_group_relationship'].current_round_data
        super(ParticipantRoundDataValue, self).__init__(*args, **kwargs)
    """
    Represents one data point collected for a given Participant in a given Round.
    """
    round_data = models.ForeignKey(RoundData, related_name='participant_data_value_set')
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='participant_data_value_set')
    submitted = models.BooleanField(default=False)
    target_data_value = models.ForeignKey('ParticipantRoundDataValue', related_name='target_data_value_set', null=True, blank=True)
    objects = PassThroughManager.for_queryset_class(ParticipantRoundDataValueQuerySet)()

    @property
    def owner(self):
        return self.participant_group_relationship

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

    def to_dict(self, cacheable=False, include_email=False):
        data = super(ParticipantRoundDataValue, self).to_dict(cacheable)
        pgr = self.participant_group_relationship
        data.update({
            'participant_group_id': pgr.pk,
            'participant_name': pgr.full_name,
            'participant_number': pgr.participant_number,
            })
        if include_email:
            data['participant_email'] = pgr.participant.email
        tdv = self.target_data_value
        if tdv is not None:
            data.update({
                'target_data_value': unicode(tdv.cached_value if cacheable else tdv.value),
                'target_parameter_name': tdv.parameter.name
                })
        return data

    def __unicode__(self):
        return u"{0} : {1} pgr:{2} ({3})".format(self.parameter, self.value, self.participant_group_relationship, self.round_data.experiment)

    class Meta:
        ordering = [ '-date_created', 'round_data', 'participant_group_relationship', 'parameter' ]
# FIXME: can't use this currently as it forbids multiple ChatMessages
#        unique_together = (('parameter', 'participant_group_relationship'),)


@simplecache
def get_chat_message_parameter():
    return Parameter.objects.get(name='chat_message', scope=Parameter.PARTICIPANT_SCOPE)

class ChatMessageQuerySet(models.query.QuerySet):

    def for_group(self, group=None, **kwargs):
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                'target_data_value__participant_group_relationship',
                ).filter(parameter=get_chat_message_parameter(), participant_group_relationship__group=group, **kwargs).order_by('-date_created')

    def message_all(self, experiment, message, round_data=None, **kwargs):
        if round_data is None:
            round_data = experiment.current_round_data
        for participant_group_relationship in ParticipantGroupRelationship.objects.for_experiment(experiment):
            yield ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                    string_value=message,
                    round_data=round_data)

class ChatMessage(ParticipantRoundDataValue):
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True, related_name='target_participant_chat_message_set')
    """ if set, this is a targeted message to the other participant in this group.  If null, this is a broadcast message to the entire group """
    objects = PassThroughManager.for_queryset_class(ChatMessageQuerySet)()

    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_chat_message_parameter()
        super(ChatMessage, self).__init__(*args, **kwargs)

    @property
    def message(self):
        return self.string_value

    @property
    def group(self):
        return self.participant_group_relationship.group

    @property
    def participant(self):
        return self.participant_group_relationship.participant

    @property
    def round_configuration(self):
        return self.round_data.round_configuration

    def to_dict(self, **kwargs):
        data = super(ChatMessage, self).to_dict(cacheable=True)
        data['message'] = self.message
        group = self.participant_group_relationship.group
        data['group_id'] = group.pk
        data['group'] = unicode(group)
        return data

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

@simplecache
def get_participant_ready_parameter():
    return Parameter.objects.get(name='participant_ready', scope=Parameter.PARTICIPANT_SCOPE)

class Comment(ParticipantRoundDataValue):
    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_comment_parameter()
        super(Comment, self).__init__(*args, **kwargs)

    @property
    def message(self):
        return self.string_value

    def to_dict(self):
        data = super(Comment, self).to_dict(cacheable=True)
        data['message'] = self.message
        return data

    class Meta:
        ordering = ['date_created']

class Like(ParticipantRoundDataValue):
    def __init__(self, *args, **kwargs):
        kwargs['parameter'] = get_like_parameter()
        super(Like, self).__init__(*args, **kwargs)

    def to_dict(self):
        data = super(Like, self).to_dict(cacheable=True)
        return data

class ActivityLog(models.Model):
    log_message = models.TextField()
    date_created = models.DateTimeField(default=datetime.now)
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


class ExperimentSession(models.Model):
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='experiment_session_set')
    date_created = models.DateTimeField(default=datetime.now)
    scheduled_date = models.DateTimeField()
    scheduled_end_date = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=20)
    creator = models.ForeignKey(User, related_name='experiment_session_set')
# FIXME: this gets copied over from the ExperimentConfiguration?
    invitation_text = models.TextField(null=True, blank=True)

class Invitation(models.Model):
    participant = models.ForeignKey(Participant)
    experiment_session = models.ForeignKey(ExperimentSession)
    date_created = models.DateTimeField(default=datetime.now)
    sender = models.ForeignKey(User)

class ParticipantSignup(models.Model):
    participant = models.ForeignKey(Participant, related_name='signup_set')
    invitation = models.ForeignKey(Invitation, related_name='signup_set')
    date_created = models.DateTimeField(default=datetime.now)
    attendance = models.PositiveIntegerField(max_length=1, null=True, blank=True, choices=((0, 'participated'), (1, 'turned away'), (2, 'absent')))

class SpoolParticipantStatistics(models.Model):
    participant = models.ForeignKey(Participant, related_name='spool_statistics_set')
    absences = models.PositiveIntegerField(default=0)
    discharges = models.PositiveIntegerField(default=0)
    participations = models.PositiveIntegerField(default=0)
    invitations = models.PositiveIntegerField(default=0)

def is_experimenter(user, experimenter=None):
    """
    returns true if user.experimenter exists and is an Experimenter instance.  If an experimenter is passed in as a
    keyword argument, adds the additional constraint that user.experimenter == experimenter
    """
    if hasattr(user, 'experimenter') and isinstance(user.experimenter, Experimenter):
        return user.experimenter.approved and (experimenter is None or user.experimenter == experimenter)
    return False

def is_participant(user):
    """
    returns true if user.participant exists and is a Participant instance.
    """
    return hasattr(user, 'participant') and isinstance(user.participant, Participant)

# signal handlers for socialauth
@receiver(social_auth.signals.socialauth_registered, sender=None)
def handle_new_socialauth_user(sender, user, response, details, **kwargs):
    logger.debug("new socialauth user: %s, %s, %s, %s", user, response, details, kwargs)
    participant = Participant.objects.create(user=user)
# add participant to each available open experiment
    for experiment in Experiment.objects.public():
        experiment.add_participant(participant)


@receiver(social_auth.signals.pre_update, sender=FacebookBackend)
def facebook_extra_values(sender, user, response, details, **kwargs):
    user.gender = response.get('gender')
    return True

def reset_password(email, from_email='vcweb@asu.edu', template='registration/password_reset_email.html'):
    """
    Reset the password for all (active) users with given E-Mail address
    """
    form = PasswordResetForm({'email': email, })
    return form.save(from_email=from_email, email_template_name=template)

