from collections import defaultdict
from datetime import datetime, timedelta
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
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.managers import InheritanceManager, PassThroughManager
from string import Template
from social_auth.backends.facebook import FacebookBackend
import social_auth.signals

from vcweb.core import signals, simplecache, dumps

import base64
import hashlib
import itertools
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
    '''
    Simple object wrapper that returns the wrapped value on any attribute reference
    '''
    def __init__(self, value):
        self.value = value
    def __getattr__(self, name):
        return self.value

class ParameterValueMixin(object):
    def get_parameter_value(self, parameter=None, name=None, default=None):
        if parameter is None and name is None:
            logger.error("Can't lookup parameter values with no name or parameter, returning default %s", default)
            return DefaultValue(default)
        parameter_value_set = self.parameter_value_set
        try:
            if parameter:
                return parameter_value_set.get(parameter=parameter)
            elif name:
                return parameter_value_set.get(parameter__name=name)
        except parameter_value_set.model.DoesNotExist as e:
            logger.debug("%s: (lookup %s %s) returning default %s", e, parameter, name, default)
            return DefaultValue(default)

class DataValueMixin(object):
    '''
    this mixin will only work on model classes that expose an "experiment" property.
    '''
    def _data_parameter_criteria(self, parameter=None, parameter_name=None, round_data=None, **kwargs):
        # FIXME: do we need to provide a mechanism for finding inactive data values?
        return dict([
            ('is_active', True),
            ('parameter', parameter) if parameter else ('parameter__name', parameter_name),
            ('round_data', self.current_round_data if round_data is None else round_data)
            ], **kwargs)

    def get_data_value(self, parameter=None, parameter_name=None, round_data=None, filter=False, default=None):
        if round_data is None:
            round_data = self.experiment.current_round_data
        criteria = self._data_parameter_criteria(parameter=parameter, parameter_name=parameter_name, round_data=round_data)
        data_value_set = self.data_value_set.select_related('parameter')
        data_value_class = data_value_set.model
        try:
            if filter:
                return data_value_set.filter(**criteria)
            else:
                return data_value_set.get(**criteria)
        except data_value_class.DoesNotExist as e:
            if default is None:
                raise e
            else:
                return DefaultValue(default)

    def copy_to_next_round(self, *data_values, **kwargs):
        e = self.experiment
        if e.is_last_round:
            return
        next_round_data = kwargs.get('next_round_data', None)
        if not next_round_data:
            next_round_data, created = e.get_or_create_round_data(round_configuration=e.next_round)
        for existing_dv in data_values:
            # Taking advantage of a trick from here:
            # http://stackoverflow.com/questions/12182657/copy-or-clone-an-object-instance-in-django-python
            existing_dv.pk = None
            existing_dv.round_data = next_round_data
            existing_dv.save()

    def set_data_value(self, parameter=None, value=None, round_data=None, **kwargs):
        if parameter is None or value is None:
            raise ValueError("need parameter and value to set")
        if round_data is None:
            round_data = self.current_round_data
        dv = self.get_data_value(round_data=round_data, parameter=parameter, **kwargs)
        dv.value = value
        dv.save()


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

class ExperimentMetadataManager(models.Manager):
    def get_by_natural_key(self, key):
        return self.get(namespace=key)

class ExperimentMetadata(models.Model):
    """
    An ExperimentMetadata record represents the *type* of a given implemented Experiment, e.g., **forestry**, **lighter
    footprints**, **boundary effects**, or **irrigation**.  This shouldn't be confused with a specific instance of a
    **forestry** or ** lighter footprints ** experiment, which represents a concrete experiment run, with a specific
    configuration, experimenter, etc.  Each experiment metadata app should define and add a single ExperimentMetadata
    record for the experiment type that it represents.  You can register an ExperimentMetadata object by creating a
    JSON/YAML/SQL representation of it in your app/fixtures directory (e.g., irrigation/fixtures/irrigation.json) and
    then invoking ``python manage.py loaddata irrigation``.
    """
    title = models.CharField(max_length=255)
    # the URL fragment that this experiment_metadata will occupy,
    namespace_regex = re.compile(r'^(?:[/]?[a-z0-9_]+\/?)+$')
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=namespace_regex)])
    # short name slug
    short_name = models.SlugField(max_length=32, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    about_url = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    default_configuration = models.ForeignKey('ExperimentConfiguration', null=True, blank=True)

    objects = ExperimentMetadataManager()

    def to_dict(self, include_configurations=False, **kwargs):
        data = {
                'title': self.title,
                'namespace': self.namespace,
                'date_created': self.date_created,
                'description': self.description,
                }
        if include_configurations:
            configurations = [ec.to_dict() for ec in ExperimentConfiguration.objects.select_related('creator').filter(experiment_metadata=self)]
            data['configurations'] = configurations
        return data

    def natural_key(self):
        return [self.namespace]

    def __unicode__(self):
        return u"%s (%s)" % (self.title, self.namespace)

    class Meta:
        ordering = ['namespace', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
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
    authentication_token = models.CharField(max_length=64, blank=True)

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

class BookmarkedExperimentMetadata(models.Model):
    experimenter = models.ForeignKey(Experimenter, related_name='bookmarked_experiment_metadata_set')
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='bookmarked_experiment_metadata_set')
    date_created = models.DateTimeField(default=datetime.now)

    class Meta:
        unique_together = (('experimenter', 'experiment_metadata'),)
        ordering = ['experimenter', 'experiment_metadata']

class ExperimenterRequest(models.Model):
    """
    a request for this user to be an experimenter, should notify admins
    """
    user = models.OneToOneField(User, verbose_name=u'Django User', unique=True)
    date_created = models.DateTimeField(default=datetime.now)
    approved = models.BooleanField(default=False)

class ExperimentConfiguration(models.Model, ParameterValueMixin):
    """
    The configuration for a given Experiment instance.  One ExperimentConfiguration can be applied to many Experiment
    instances but can only be associated to a single ExperimentMetadata record.
    """
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='experiment_configuration_set')
    creator = models.ForeignKey(Experimenter, related_name='experiment_configuration_set')
    name = models.CharField(max_length=255)
    max_number_of_participants = models.PositiveIntegerField(default=0)
    invitation_subject = models.TextField(blank=True, help_text=_('subject header for email registrations'))
    invitation_text = models.TextField(blank=True, help_text=_('text to send out via email invitations'))
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    is_public = models.BooleanField(default=False)
    max_group_size = models.PositiveIntegerField(default=5)
    exchange_rate = models.DecimalField(null=True, blank=True, default=0.2, max_digits=6, decimal_places=2, help_text=_('The exchange rate of currency per in-game token, e.g., dollars per token'))
    treatment_id = models.CharField(blank=True, max_length=32, help_text=_('An alphanumeric ID that should be unique to the set of ExperimentConfigurations for a given ExperimentMetadata'))
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


    def to_dict(self, **kwargs):
        return {
                'pk': self.pk,
                'name': self.name,
                'treatment_id': self.treatment_id,
                'date_created': self.date_created.strftime("%m-%d-%Y %H:%M"),
                'creator': self.creator,
                'max_group_size': self.max_group_size,
                'is_experimenter_driven': self.is_experimenter_driven,
                'number_of_rounds': self.final_sequence_number,
                }


    def serialize(self, output_format='xml', **kwargs):
        if self.round_configuration_set.count() > 0:
            all_objects = []
            for rc in self.round_configuration_set.all():
                all_objects.append(rc)
                all_objects.extend(rc.parameter_value_set.all())
            all_objects.append(self)
            return serializers.serialize(output_format, all_objects, **kwargs)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['experiment_metadata', 'creator', 'date_created']


class ExperimentQuerySet(models.query.QuerySet):
    ACTIVE_STATUSES = ('ACTIVE', 'ROUND_IN_PROGRESS')
    def public(self, **kwargs):
        return self.filter(experiment_configuration__is_public=True, **kwargs)
    def archived(self, **kwargs):
        return self.completed(**kwargs)
    def completed(self, **kwargs):
        return self.filter(status='COMPLETED', **kwargs)
    def inactive(self, **kwargs):
        return self.filter(status='INACTIVE', **kwargs)
    def active(self, **kwargs):
        return self.filter(status__in=ExperimentQuerySet.ACTIVE_STATUSES, **kwargs)
    def for_participant(self, participant, **kwargs):
        return participant.experiments.filter(status__in=ExperimentQuerySet.ACTIVE_STATUSES)
    def for_experimenter(self, experimenter, **kwargs):
        return self.select_related('experimenter').filter(experimenter=experimenter, **kwargs)

class Experiment(models.Model):
    """
    An Experiment represents a concrete treatment run for a given ExperimentMetadata -- a combination of
    ExperimentMetadata and ExperimentConfiguration for a given Experimenter """
    Status = Choices(
            ('INACTIVE', _('Not active')),
            ('ACTIVE', _('Active, no round in progress')),
            ('ROUND_IN_PROGRESS', _('Round in progress')),
            ('COMPLETED', _('Completed')))
    authentication_code = models.CharField(max_length=32, default="vcweb.auth.code")
    """
    currently unused, but kept here in the event that we want to allow participants to authenticate with this
    authentication_code either in lieu or in addition to their own user password.
    """
    current_round_sequence_number = models.PositiveIntegerField(default=1, help_text=_('''One-based sequence number used to identify which round the experiment is currently running, should be a sequential number ranging from 1 to N'''))
    """ Each round is assigned a sequential sequence number, ranging from 1 to N.  Used to identify which round the experiment is currently running. """
    current_repeated_round_sequence_number = models.PositiveIntegerField(default=0, help_text=_('''For repeating rounds, the number of times the round has been repeated, used to keep track of when to move on from a repeating round.'''))
    experimenter = models.ForeignKey(Experimenter)
    """ the user running this experiment """
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    """ the experiment metadata object that this experiment instance represents """
    experiment_configuration = models.ForeignKey(ExperimentConfiguration)
    """ the configuration parameters in use for this experiment run. """
# FIXME: consider using django-model-utils but need to verify that it works with South
# status = StatusField()
    status = models.CharField(max_length=32, choices=Status, default=Status.INACTIVE)
    """
    the status of an experiment can be either INACTIVE, ACTIVE, ROUND_IN_PROGRESS, or COMPLETED
    """
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
# FIXME: inherit from TimeFramedModel instead?
    date_activated = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format
    # 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32, blank=True)
    tick_duration = models.CharField(max_length=32, blank=True)
    """ how often the experiment_metadata server should tick. """

    current_round_start_time = models.DateTimeField(null=True, blank=True)
    """ elapsed time in seconds for the current round. """
    amqp_exchange_name = models.CharField(max_length=64, default="vcweb.default.exchange")

    cached_round_sequence_number = None
    ''' used to cache the round configuration '''

    objects = PassThroughManager.for_queryset_class(ExperimentQuerySet)()

    @property
    def is_time_expired(self):
        return self.current_round_elapsed_time >= self.current_round.duration

    @property
    def is_round_in_progress(self):
        return self.status == Experiment.Status.ROUND_IN_PROGRESS

    @property
    def is_data_round_in_progress(self):
        return self.is_round_in_progress and self.current_round.is_playable_round

    @property
    def total_elapsed_time(self):
        if self.date_activated:
            return datetime.now() - self.date_activated
        return timedelta(0)

    @property
    def current_round_elapsed_time(self):
        if self.current_round_start_time and self.is_timed_round:
            return datetime.now() - self.current_round_start_time
        return timedelta(0)

    @property
    def time_remaining(self):
        if self.is_timed_round:
            tr = self.current_round.duration - self.current_round_elapsed_time.seconds
            if tr <= 0:
                return u"Expired (%s seconds ago)" % abs(tr)
            return tr
        else:
            return "Untimed round (advance manually or via automated checkpointing)"

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
    def number_of_participants(self):
        return self.participant_set.count()

    @property
    def current_session_id(self):
        return self.current_round.session_id

    @property
    def groups(self):
        return self.group_set.filter(session_id=self.current_session_id)

    @property
    def active_group_clusters(self):
        return (group_cluster for group_cluster in self.group_cluster_set.filter(session_id=self.current_session_id))

    @property
    def participant_group_relationships(self):
        return ParticipantGroupRelationship.objects.select_related('group').filter(group__in=self.groups)

    @property
    def display_name(self):
        return self.experiment_metadata.title

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

# FIXME: remove these after new model of dashboard experiment controller is done
# The following URL helper properties are generic experiment management URLs
# available to experimenters but not participants
    @property
    def management_url(self):
        return "/%s/experimenter" % self.get_absolute_url()

    @property
    def monitor_url(self):
        return "%s/monitor" % self.controller_url

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
    def participant_template(self):
        return "%s/participate.html" % self.experiment_metadata.namespace

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
        ps = dict(round_configuration=round_configuration)
        if round_configuration.is_repeating_round:
            ps.update(repeating_round_sequence_number=self.current_repeated_round_sequence_number)
        return RoundData.objects.select_related('round_configuration').get(experiment=self, **ps)

    @property
    def playable_round_data(self):
        return self.round_data_set.select_related('experiment', 'round_configuration').filter(round_configuration__round_type__in=RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS,
                round_configuration__sequence_number__lte=self.current_round_sequence_number)

    @property
    def all_chat_messages(self):
        return ChatMessage.objects.for_experiment(self)

    @property
    def should_repeat(self):
        cr = self.current_round
        return cr.is_repeating_round and self.current_repeated_round_sequence_number < cr.repeat

    @property
    def next_round(self):
        current_round = self.current_round
        if not self.should_repeat and self.has_next_round:
            return self.get_round_configuration(self.current_round_sequence_number + 1)
        else:
            return current_round

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
        return self.status not in (Experiment.Status.COMPLETED, Experiment.Status.INACTIVE,)

    @property
    def is_archived(self):
        # FIXME: add a unique status for this if needed
        return self.status == Experiment.Status.COMPLETED

    @property
    def is_completed(self):
        return self.status == Experiment.Status.COMPLETED

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
    def number_of_ready_participants(self):
        if self.is_round_in_progress:
            return ParticipantRoundDataValue.objects.filter(parameter=get_participant_ready_parameter(), round_data=self.current_round_data, boolean_value=True).count()
        else:
            return 0

    def all_participants_submitted(self, parameter, round_data=None):
        if round_data is None:
            round_data = self.current_round_data
        return ParticipantRoundDataValue.objects.filter(parameter=parameter, submitted=True, round_data=round_data).count() == self.participant_set.count()

    @property
    def all_participants_ready(self):
        return self.number_of_ready_participants == self.participant_set.count()

    def get_participant_experiment_relationship(self, participant):
        return self.participant_relationship_set.select_related('participant__user').get(participant=participant)

    def get_participant_group_relationship(self, participant=None, participant_pk=None):
        session_id = self.current_round.session_id
        criteria = dict([
            ('group__experiment', self),
            ('participant__pk', participant_pk) if participant_pk else ('participant', participant),
            ('group__session_id', session_id),
            ])
        return ParticipantGroupRelationship.objects.get(**criteria)

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
            email_messages.append(self.create_registration_email(per, password=password, is_new_participant=created))
        if email_messages:
            mail.get_connection().send_messages(email_messages)

    def create_registration_email(self, participant_experiment_relationship, password='', **kwargs):
        '''
        Override the email template by creating <experiment-namespace>/email/experiment-registration(txt|html) template files
        '''
        logger.debug("sending email to %s", participant_experiment_relationship.participant)
        plaintext_template = select_template(['%s/email/experiment-registration.txt' % self.namespace, 'email/experiment-registration.txt'])
        html_template = select_template(['%s/email/experiment-registration.html' % self.namespace, 'email/experiment-registration.html'])
        experiment = participant_experiment_relationship.experiment
        participant = participant_experiment_relationship.participant
        user = participant.user
        if not password.strip():
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
        to_address = [ participant_experiment_relationship.participant.email ]
        bcc_address = [ experimenter_email ]
        msg = EmailMultiAlternatives(subject, plaintext_content, experimenter_email, to_address, bcc_address)
        msg.attach_alternative(html_content, "text/html")
        return msg

    ''' FIXME: get rid of hardcoded defaults for the slovakia pretest '''
    def setup_test_participants(self, count=20, institution=None, email_suffix='mailinator.com', username_suffix='asu', password='test'):
        if self.participant_set.count() > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, self.participant_set.count())
            return
        users = []
        for i in xrange(1, count+1):
            email = u's%d%s@%s' % (i, username_suffix, email_suffix)
            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                user = User.objects.create_user(username=email, email=email, password=password)
                user.first_name = u'Student'
                user.last_name = u"%d" % i
                user.save()
            users.append(user)
        self.register_participants(users=users, institution=institution, password=password)

# FIXME: figure out how to declaratively do this so experiments can more easily notify "I have these data values to
# initialize at the start of each round.
# XXX: it can be dangerous to use empty lists as initial keyword args but we only iterate over them (e.g.,
# http://effbot.org/zone/default-values.htm)
# defaults map parameter model instances to their default initial value, e.g., { footprint-level-parameter: 1, resource-level-parameter: 100 }
    def initialize_data_values(self, group_parameters=[], participant_parameters=[], group_cluster_parameters=[], round_data=None, defaults={}):
        logger.debug("initializing [participant params: %s]  [group parameters: %s] [group_cluster_parameters: %s] ", participant_parameters, group_parameters, group_cluster_parameters)
        if round_data is None:
            round_data = self.current_round_data
        parameter_defaults = defaultdict(dict)
        for parameter in itertools.chain(participant_parameters, group_parameters, group_cluster_parameters):
            if parameter in defaults:
                parameter_defaults[parameter] = { parameter.value_field_name: defaults[parameter] }
        logger.debug("parameter default values: %s", parameter_defaults)
# create group cluster parameter data values
        if group_cluster_parameters:
            for group_cluster in self.active_group_clusters:
                for parameter in group_cluster_parameters:
                    gcdv, created = GroupClusterDataValue.objects.get_or_create(round_data=round_data, parameter=parameter, group_cluster=group_cluster,
                            defaults=parameter_defaults[parameter])
                    #logger.debug("%s (%s)", gcdv, created)
        for group in self.groups:
            for parameter in group_parameters:
                group_data_value, created = GroupRoundDataValue.objects.get_or_create(round_data=round_data, group=group, parameter=parameter, defaults=parameter_defaults[parameter])
                #logger.debug("%s (%s)", group_data_value, created)
            if participant_parameters:
                for pgr in group.participant_group_relationship_set.all():
                    for parameter in participant_parameters:
                        participant_data_value, created = ParticipantRoundDataValue.objects.get_or_create(round_data=round_data, participant_group_relationship=pgr, parameter=parameter,
                                defaults=parameter_defaults[parameter])
                #        logger.debug("%s (%s)", participant_data_value, created)

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

    def add_participant(self, participant, current_group=None, max_group_size=None, session_id=None):
        # FIXME: simplify logic where possible
        if participant not in self.participant_set.all():
            logger.warning("participant %s not a member of this experiment %s, adding them", participant, self)
            ParticipantExperimentRelationship.objects.create(participant=participant, experiment=self,
                    created_by=participant.user)
        pgrs = ParticipantGroupRelationship.objects.filter(group__experiment=self, participant=participant)
        if current_group is None:
            # try to add them to the last group in group_set with the same session id
            session_id_groups  = self.group_set.filter(session_id=session_id)
            if session_id_groups:
                current_group = session_id_groups.reverse()[0]
            number_of_groups = self.group_set.count()
            if current_group is None or number_of_groups == 0:
                # create a new group
                current_group = self.group_set.create(number=number_of_groups, max_size=max_group_size, session_id=session_id)

        if pgrs.count() > 0:
            # ensure that any existing group that this participant is in has a different session id from this group
            for pgr in pgrs:
                if pgr.group.session_id == current_group.session_id:
                    logger.error("Participant %s is already in a group %s with the same session id, not adding them to %s", participant, pgr.group, current_group)
                    return pgr
        return current_group.add_participant(participant)

    def allocate_groups(self, randomize=True, preserve_existing_groups=False, session_id=''):
        logger.debug("allocating groups for %s with session_id %s (randomize? %s)" % (self, session_id, randomize))
        # clear out all existing groups
        # FIXME: record previous mappings in activity log.
        max_group_size = self.experiment_configuration.max_group_size
        participants = list(self.participant_set.all())
        if randomize:
            random.shuffle(participants)

        gs = self.group_set
        if gs.count() > 0:
            if preserve_existing_groups:
                logger.debug("preserving existing groups")
                # verify incoming session id is an actual value
                if not session_id:
                    round_configuration = self.current_round
                    session_id = round_configuration.session_id
                    if not session_id:
                        logger.error("Trying to create a new set of groups but no session id has been set on %s.  Aborting.", round_configuration)
                        raise ValueError("Cannot allocate new groups and preserve existing groups without an appropriate session id set on this round configuration %s" % round_configuration)
            else:
                logger.debug("deleting old groups")
                gqs = gs.all()
                for g in gqs:
                    self.log("reallocating/deleting group %s" % g.participant_group_relationship_set.all())
                gqs.delete()
# add each participant to the next available group
        current_group = None
        for p in participants:
            pgr = self.add_participant(p, current_group, max_group_size, session_id)
            current_group = pgr.group
        self.create_group_clusters()

    def create_group_clusters(self):
        round_configuration = self.current_round
        session_id = round_configuration.session_id
        if round_configuration.create_group_clusters:
            logger.debug("creating group clusters with session id %s", session_id)
            gcs = self.group_cluster_set.filter(session_id=session_id)
            gs = self.group_set.filter(session_id=session_id)
            gcs.delete()
            group_cluster_size = round_configuration.group_cluster_size
            groups = list(gs)
            if len(groups) % group_cluster_size != 0:
                logger.error("trying to create clusters of size %s but we have %s groups which isn't evenly divisible - aborting.",
                        group_cluster_size, len(groups))
                return
            random.shuffle(groups)
            gc = GroupCluster.objects.create(session_id=session_id, experiment=self)
            for group in groups:
                if gc.group_relationship_set.count() == group_cluster_size:
                    gc = GroupCluster.objects.create(session_id=session_id, experiment=self)
# adding group clusters
                gc.add(group)

    def get_round_configuration(self, sequence_number):
        return RoundConfiguration.objects.get(experiment_configuration__experiment=self, sequence_number=sequence_number)

    def get_template_path(self, name):
        return "%s/%s" % (self.namespace, name)

    # XXX: decide whether or not to include this ability in the interface.
    def move_to_previous_round(self):
        # FIXME: doesn't take into account repeating rounds at the moment
        if self.is_round_in_progress:
            self.end_round()
        self.current_round_elased_time = 0
        self.current_round_sequence_number = max(self.current_round_sequence_number - 1, 1)
        self.save()

    ACCEPTABLE_ACTIONS = ('advance_to_next_round', 'end_round', 'start_round', 'move_to_previous_round', 'activate',
            'deactivate', 'complete', 'restart_round', 'restart')
    def invoke(self, action_name, experimenter=None):
        if action_name in Experiment.ACCEPTABLE_ACTIONS:
            logger.debug("experimenter %s invoking action %s", experimenter, action_name)
            action = getattr(self, action_name)
            return action()
        else:
            raise AttributeError("Invalid experiment action %s requested of experiment %s" % (action_name, self))

    def advance_to_next_round(self):
        if self.is_round_in_progress:
            self.end_round()
        if self.should_repeat:
            self.current_repeated_round_sequence_number += 1
        elif self.has_next_round:
# advance sequence number and blank out repeated round sequence number if necessary
            self.current_round_sequence_number += 1
            self.current_repeated_round_sequence_number = 0
        else:
            logger.warning("trying to advance past the last round - no-op")
            return
        return self.start_round()

    def get_or_create_round_data(self, round_configuration=None):
        if round_configuration is None:
            round_configuration = self.current_round
        ps = dict(round_configuration=round_configuration)
        if round_configuration.is_repeating_round:
            # create round data with repeating sequence number
            ps['repeating_round_sequence_number'] = self.current_repeated_round_sequence_number
        round_data, created = self.round_data_set.get_or_create(**ps)
        if self.experiment_configuration.is_experimenter_driven:
            # create participant ready data values for every round in experimenter driven experiments
            logger.debug("creating participant ready participant round data values for experimenter driven experiment")
            for pgr in self.participant_group_relationships:
                ParticipantRoundDataValue.objects.get_or_create(participant_group_relationship=pgr,
                        parameter=get_participant_ready_parameter(), round_data=round_data, defaults={'boolean_value': False})
        if not created:
            logger.debug("already created round data: %s", round_data)
        return round_data, created

    def start_round(self, sender=None):
        logger.debug("%s STARTING ROUND (sender: %s)", self, sender)
        self.status = Experiment.Status.ROUND_IN_PROGRESS
        current_round_configuration = self.current_round
        if current_round_configuration.randomize_groups:
            self.allocate_groups(
                    preserve_existing_groups=current_round_configuration.preserve_existing_groups,
                    session_id=current_round_configuration.session_id)
        # XXX: must create round data AFTER group allocation so that any participant round data values
        # (participant ready parameters for instance) are associated with the correct participant group
        # relationships.
        self.get_or_create_round_data()
        self.current_round_start_time = datetime.now()
        self.log('Starting round')
        self.save()
        # notify registered game handlers
        if sender is None:
            sender = intern(self.experiment_metadata.namespace.encode('utf8'))
        signal_tuple = signals.round_started.send_robust(sender, experiment=self, time=datetime.now(), round_configuration=current_round_configuration)
        self._check_signal_result(signal_tuple)
        return signal_tuple

    def _check_signal_result(self, signal_tuple_list):
        logger.debug("checking signal tuple list: %s", signal_tuple_list)
        for signal_tuple in signal_tuple_list:
            if signal_tuple[1] is not None:
                logger.error("%s resulted in an error condition: %s", signal_tuple[0], signal_tuple[1])

    def stop_round(self, sender=None, **kwargs):
        return self.end_round()

    def end_round(self, sender=None):
        self.status = Experiment.Status.ACTIVE
        self.save()
        self.log('Ending round with elapsed time %s' % self.current_round_elapsed_time)
        sender = intern(self.experiment_metadata.namespace.encode('utf8')) if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        logger.debug("about to send round ended signal with sender %s", sender)
        signal_tuple = signals.round_ended.send_robust(sender, experiment=self, round_configuration=self.current_round)
        self._check_signal_result(signal_tuple)
        return signal_tuple

    def activate(self):
        if self.is_archived:
            logger.debug("ignoring request to activate archived experiment, need manual intervention to perform this as it would wipe existing data.")
        elif not self.is_active:
            self.allocate_groups()
            self.status = Experiment.Status.ACTIVE
            self.date_activated = datetime.now()
            self.start_round()
        return self

    def restart(self):
        self.log("Restarting experiment entirely from the first round.")
        self.deactivate()
        self.current_round_sequence_number = 1
        self.activate()
        self.start_round()

    def restart_round(self):
        self.stop_round()
        self.start_round()

    def complete(self):
        self.log("Marking as COMPLETED")
        self.status = Experiment.Status.COMPLETED
        self.save()

    def deactivate(self):
        self.log("Deactivating experiment and flagging as inactive.")
        self.status = Experiment.Status.INACTIVE
        self.save()

    def check_elapsed_time(self):
        if self.is_timed_round and self.is_time_expired:
            self.end_round()

    def all_round_data(self):
        # FIXME: figure out a better way to convert these to json that doesn't involve manual remapping of attribute names...
        # or be consistent so that things on the client side are named the same as the server side
        all_round_data = []
        for round_data in self.round_data_set.select_related('round_configuration').reverse():
            # XXX: grossly inefficient as number of rounds increases, load them dynamically instead when the accordion is opened
            # group_data_values = [gdv.to_dict(cacheable=True) for gdv in round_data.group_data_value_set.select_related('group', 'parameter').all()]
            # participant_data_values = [pdv.to_dict(include_email=True, cacheable=True) for pdv in round_data.participant_data_value_set.select_related('participant_group_relationship__participant__user', 'parameter').exclude(parameter=get_chat_message_parameter())]
            rc = round_data.round_configuration
            all_round_data.append({
                'pk': round_data.pk,
                'roundDataId': "roundData_%s" % round_data.pk,
                'experimenterNotes': round_data.experimenter_notes,
                'roundType': rc.get_round_type_display(),
                'roundNumber': rc.round_number,
                # empty stubs to be loaded in dynamically when loaded
                'groupDataValues': [],
                'participantDataValues': [],
                })
        return all_round_data

    def to_dict(self, include_round_data=False, default_value_dict=None, attrs=None, *args, **kwargs):
        ec = self.experiment_configuration
        experiment_dict = dict(default_value_dict or {}, **kwargs)
        experiment_dict.update({
                'roundStatusLabel': self.status_label,
                'roundSequenceLabel': self.sequence_label,
                'timeRemaining': self.time_remaining,
                'currentRoundStartTime': self.current_round_start_time.strftime('%c') if self.current_round_start_time else 'N/A',
                'participantCount': self.participant_set.count(),
                'isRoundInProgress': self.is_round_in_progress,
                'isActive': self.is_active,
                'isArchived': self.is_archived,
                'exchangeRate': float(ec.exchange_rate),
                'readyParticipants': self.number_of_ready_participants,
                'status': self.status,
                })
        if include_round_data:
            # XXX: stubs for round data 
            experiment_dict['allRoundData'] = self.all_round_data()
            experiment_dict['chatMessages'] = [chat_message.to_dict() for chat_message in self.all_chat_messages]
            experiment_dict['messages'] = map(str, self.activity_log_set.order_by('-date_created')[:100])
            experiment_dict['experimenterNotes'] = self.current_round_data.experimenter_notes if self.is_round_in_progress else ''
            experiment_dict['groups'] = [group.to_dict() for group in self.groups]
# FIXME: remove if unused/unneeded, intended to provide some way to include more experiment attributes at invocation time
        if attrs:
            experiment_dict.update([(attr, getattr(self, attr, None)) for attr in attrs])
        return experiment_dict

    def as_dict(self, *args, **kwargs):
        return self.to_dict(*args, **kwargs)

    def to_json(self, include_round_data=False, *args, **kwargs):
        return dumps(self.to_dict(include_round_data, *args, **kwargs))

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
                          status=Experiment.Status.INACTIVE
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

class RoundConfiguration(models.Model, ParameterValueMixin):
    # FIXME: refactor this into a single data structure
    # maps round type name to (description, default_template_filename)
    ROUND_TYPES_DICT = dict(
            WELCOME=('Initial welcome round', 'welcome.html'),
            GENERAL_INSTRUCTIONS=('General instructions round (introduction)', 'general-instructions.html'),
            REGULAR=('Regular experiment round', 'participate.html'),
            CHAT=('Chat round', 'chat.html'),
            DEBRIEFING=('Debriefing round', 'debriefing.html'),
            INSTRUCTIONS=('Instructions round', 'instructions.html'),
            PRACTICE=('Practice round', 'practice.html'),
            QUIZ=('Quiz round', 'quiz.html'))
    ROUND_TYPES = (CHAT, DEBRIEFING, GENERAL_INSTRUCTIONS, INSTRUCTIONS, PRACTICE, QUIZ, REGULAR, WELCOME) = sorted(ROUND_TYPES_DICT.keys())

    RoundType = Choices(*[(round_type, ROUND_TYPES_DICT[round_type][0]) for round_type in ROUND_TYPES])
    PLAYABLE_ROUND_CONFIGURATIONS = (RoundType.PRACTICE, RoundType.REGULAR)

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
    instructions = models.TextField(blank=True)
    """ instructions, if any, to display before the round begins """
    debriefing = models.TextField(blank=True)
    """ debriefing, if any, to display after the round ends """
    round_type = models.CharField(max_length=32,
                                  choices=RoundType,
                                  default=RoundType.REGULAR)
    """
    name of a custom template to be used this round.  e.g., if set to
    quiz_2.html in the forestry experiment app, this would be loaded from
    forestry/templates/forestry/quiz_2.html
    """
    template_filename = models.CharField(max_length=64, blank=True,
            help_text=_('''The filename of the template to use to render when executing this round.
                        This file should exist in your templates directory as your-experiment-namespace/template-name.html,
                        e.g., if set to foo.html, vcweb will look for templates/forestry/foo.html'''))
    template_id = models.CharField(max_length=128, blank=True,
            help_text=_('A HTML template ID to use in a single page app, e.g., KO template'))
    survey_url = models.URLField(null=True, blank=True)
    """ external survey url """
    chat_enabled = models.BooleanField(default=False, help_text=_("Is chat enabled in this round?"))
    create_group_clusters = models.BooleanField(default=False, help_text=_("Create relationships (clusters) of groups that can share group cluster data values"))
    group_cluster_size = models.PositiveIntegerField(null=True, blank=True, default=2, help_text=_("How many groups should form a cluster?"))
    randomize_groups = models.BooleanField(default=False, help_text=_("Shuffle participants into new groups when the round begins?"))
    """ Should groups be randomized at the start of the round? """
    preserve_existing_groups = models.BooleanField(default=True, help_text=_("This option is only useful if randomize_groups is set to true.  If we are randomizing groups, should existing groups (if any) be preserved?"))
    """ Should existing groups (if any) be preserved? """
    session_id = models.CharField(max_length=64, blank=True,
            default='',
            help_text=_('''
            Session id to associate with this round data and the groups in this experiment, useful for longer
            multi-session experiments where group membership may change.  We don't want to destroy the old groups as
            that information is still needed to determine payments, etc. Instead we need to create a new set of
            Group/ParticipantGroupRelationship models that can live in conjunction with the existing
            Group/ParticipantGroupRelationship models.
            '''))
    repeat = models.PositiveIntegerField(default=0, help_text=_('If set to a positive integer n, this round will repeat itself n times with the same configuration and parameter values.'))

    @property
    def custom_template_filename(self):
        return self.template_filename if self.template_filename else self.default_template_filename

    @property
    def default_template_filename(self):
        return RoundConfiguration.ROUND_TYPES_DICT[self.round_type][1]

    def get_custom_instructions(self, context_dict=None, **kwargs):
        '''
        FIXME: deprecated in favor of RoundConfiguration.template_id approach
        '''
        if not self.is_instructions_round:
            logger.warning("tried to get custom instructions for a non-instructions round %s", self)
            return None
        try:
            instructions_template = select_template([self.template_path])
            if context_dict is None:
                context_dict = {}
            context_dict.update(kwargs, session_number=self.session_id)
            c = Context(context_dict)
            return instructions_template.render(c)
        except:
            logger.warning("no template found for custom instructions: %s", self.template_path)
            return None

    @property
    def template_name(self):
        return self.template_id if self.template_id else self.round_type

    @property
    def template_path(self):
        return "%s/%s" % (self.experiment_configuration.namespace, self.custom_template_filename)

    @property
    def round_number(self):
        return self.sequence_number if self.display_number == 0 else self.display_number

    @property
    def is_repeating_round(self):
        return self.repeat > 0

    @property
    def is_debriefing_round(self):
        return self.round_type == RoundConfiguration.RoundType.DEBRIEFING

    @property
    def is_chat_round(self):
        return self.round_type == RoundConfiguration.RoundType.CHAT

    @property
    def is_instructions_round(self):
        return self.round_type in (RoundConfiguration.RoundType.INSTRUCTIONS, RoundConfiguration.RoundType.GENERAL_INSTRUCTIONS)

    @property
    def is_quiz_round(self):
        return self.round_type == RoundConfiguration.RoundType.QUIZ

    @property
    def is_practice_round(self):
        return self.round_type == RoundConfiguration.RoundType.PRACTICE

    @property
    def is_regular_round(self):
        return self.round_type == RoundConfiguration.RoundType.REGULAR

    @property
    def is_playable_round(self):
        return self.round_type in RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS

    @property
    def is_survey_enabled(self):
        survey_url = getattr(self, 'survey_url', None)
        return survey_url is not None and survey_url

    def get_debriefing(self, participant_id=None, **kwargs):
        return self.templatize(self.debriefing, participant_id, kwargs)

    def get_instructions(self, participant_id=None, **kwargs):
        return self.templatize(self.instructions, participant_id, kwargs)


    def templatize(self, template_string, participant_id=None, **kwargs):
        return Template(template_string).substitute(kwargs, round_number=self.display_number, participant_id=participant_id)

    def __unicode__(self):
        return u"%s %s (%s %s)" % (self.get_round_type_display(), self.sequence_label, self.experiment_configuration, self.session_id)

    @property
    def display_label(self):
        return u"Round %d" % self.round_number if self.is_regular_round else self.get_round_type_display()

    @property
    def sequence_label(self):
        return u"%d of %d" % (self.sequence_number, self.experiment_configuration.final_sequence_number)

    class Meta:
        ordering = [ 'experiment_configuration', 'sequence_number', 'date_created' ]

class QuizQuestion(models.Model):
    '''
    FIXME: deprecated, place quiz and quiz logic inline in the client, have the form submit the responses and correct
    answers to the server-side.
    '''
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
        return self.get(scope=Parameter.Scope.PARTICIPANT, **kwargs)

    def for_group(self, **kwargs):
        return self.get(scope=Parameter.Scope.GROUP, **kwargs)

    def for_round(self, **kwargs):
        return self.get(scope=Parameter.Scope.ROUND, **kwargs)

    def for_experiment(self, **kwargs):
        return self.get(scope=Parameter.Scope.EXPERIMENT, **kwargs)

    def for_group_cluster(self, **kwargs):
        return self.get(scope=Parameter.Scope.GROUP_CLUSTER, **kwargs)

class ParameterPassThroughManager(PassThroughManager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Parameter(models.Model):
    ParameterType = Choices(
            ('int', 'Integer value'),
            ('string', 'String value'),
            ('foreignkey', 'Foreign key'),
            ('float', 'Floating-point number'),
            ('boolean', 'Boolean value (true/false)'),
            ('enum', 'Enumeration'))
    Scope = Choices(
            ('round', 'ROUND', 'Round configuration parameter applies across all groups for a given round'),
            ('experiment', 'EXPERIMENT', 'Experiment configuration parameter applies to the entire experiment across all groups and rounds'),
            ('group', 'GROUP', 'Parameter applies to a group for a given round'),
            ('group_cluster', 'GROUP_CLUSTER', 'Group cluster data parameter applies to a single group cluster for a given round'),
            ('participant', 'PARTICIPANT', 'Participant data parameter applies for a single participant for a given round'))
    # FIXME: arcane, see if we can encapsulate this better.  used to provide sane default values for each parameter type
    # when the parameter is null
    NONE_VALUES_DICT = dict(map(lambda x,y: (x[0], y), ParameterType, [0, '', -1, 0.0, False, None]))
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
    scope = models.CharField(max_length=32, choices=Scope, default=Scope.ROUND)
    name = models.CharField(max_length=255, unique=True)
    display_name = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=512, blank=True)
    type = models.CharField(max_length=32, choices=ParameterType)
    class_name = models.CharField(max_length=64, blank=True, help_text='Model classname in the form of appname.modelname, e.g., "core.Experiment".  Only applicable for foreign key parameters.')
    default_value_string = models.CharField(max_length=255, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    creator = models.ForeignKey(Experimenter)
    experiment_metadata = models.ForeignKey(ExperimentMetadata, null=True, blank=True)
    enum_choices = models.TextField(blank=True)
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
    string_value = models.TextField(blank=True)
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
                'parameter_label': p.label
                }
        data['value'] = unicode(self.cached_value if cacheable else self.value)
        return data

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2}".format(self.parameter, self.value, self.date_created)

    class Meta:
        abstract = True

# configuration parameters across the entire experiment
class ExperimentParameterValue(ParameterizedValue):
    experiment_configuration = models.ForeignKey(ExperimentConfiguration, related_name='parameter_value_set')

    def __unicode__(self):
        ec = self.experiment_configuration
        return u"{0} -> [{1}: {2}]".format(ec, self.parameter, self.value)

class RoundParameterValue(ParameterizedValue):
    """
    Represents a specific piece of round configuration data.
    """
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='parameter_value_set')

    def __unicode__(self):
        rc = self.round_configuration
        return u"{0}:{1} -> [{2}: {3}]".format(rc.experiment_configuration, rc.sequence_label, self.parameter, self.value)

class Group(models.Model, DataValueMixin):
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
    session_id = models.CharField(max_length=64, blank=True, default='')

    @property
    def name(self):
        return u"Group %s" % string.ascii_uppercase[self.number]

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
        return Parameter.objects.filter(experiment_metadata=self.experiment.experiment_metadata, scope=Parameter.Scope.GROUP)

    @property
    def current_round_data(self):
        return self.experiment.current_round_data

    @property
    def is_full(self):
        return self.size >= self.max_size > 0

    @property
    def is_open(self):
        return not self.is_full

    @property
    def current_round_activity_log(self):
        return self.activity_log_set.filter(round_configuration=self.current_round)

    def to_dict(self):
        participant_group_relationships = [ 
                { 'pk': pgr.pk, 'participant_number': pgr.participant_number, 'email': pgr.participant.email }
                for pgr in self.participant_group_relationship_set.all()
                ]
        return {
                'name': self.name,
                'pk': self.pk,
                'participant_group_relationships': participant_group_relationships
                }

    def get_related_group(self):
        ''' FIXME: currently only assumes single paired relationships '''
        gr = GroupRelationship.objects.get(group=self)
        related_gr = GroupRelationship.objects.select_related('group').get(~models.Q(group=self), cluster=gr.cluster)
        return related_gr.group

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

    def _data_parameter_criteria(self, parameter=None, parameter_name=None, round_data=None, **kwargs):
        criteria = dict([
            ('is_active', True),
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

    def get_participant_data_values(self, **kwargs):
        criteria = self._data_parameter_criteria(participant_group_relationship__group=self, **kwargs)
        return ParticipantRoundDataValue.objects.filter(**criteria)

    def create_next_group(self):
        return Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment,
                session_id=self.session_id)

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
        logger.debug("adding participant %s to group %s", participant, group)
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

class GroupClusterQuerySet(models.query.QuerySet):
    def for_experiment(self, experiment, **kwargs):
        return self.prefetch_related('group_relationship_set').filter(experiment=experiment, **kwargs)

class GroupCluster(models.Model, DataValueMixin):
    date_created = models.DateTimeField(default=datetime.now)
    name = models.CharField(max_length=64, blank=True)
    session_id = models.CharField(max_length=64, blank=True, default='')
    experiment = models.ForeignKey(Experiment, related_name='group_cluster_set')

    objects = PassThroughManager.for_queryset_class(GroupClusterQuerySet)()

    @property
    def size(self):
        return self.group_relationship_set.count()

    def add(self, group):
        return GroupRelationship.objects.create(cluster=self, group=group)


    def __unicode__(self):
        return u"GroupCluster #%s %s (%s)" % (self.pk, self.session_id, self.experiment)

    class Meta:
        ordering = ['date_created']

class GroupRelationship(models.Model):
    date_created = models.DateTimeField(default=datetime.now)
    cluster = models.ForeignKey(GroupCluster, related_name='group_relationship_set')
    group = models.ForeignKey(Group)

    def __unicode__(self):
        return u"%s -> %s" % (self.group, self.cluster)

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
    repeating_round_sequence_number = models.PositiveIntegerField(default=0, help_text=_('''Repeating round's sequence number used to disambiguate round data in repeating rounds.'''))
    elapsed_time = models.PositiveIntegerField(default=0)
    experimenter_notes = models.TextField(blank=True)

    @property
    def session_id(self):
        return self.round_configuration.session_id

    def __unicode__(self):
        return u"Data for Round %s (%s)" % (self.round_configuration.sequence_number, self.round_configuration.get_round_type_display())

    class Meta:
        ordering = [ 'round_configuration' ]
        unique_together = (('round_configuration', 'repeating_round_sequence_number', 'experiment'),)

class GroupClusterDataValue(ParameterizedValue):
    group_cluster = models.ForeignKey(GroupCluster, related_name='data_value_set')
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
    current_location = models.CharField(max_length=64, blank=True)
# arbitrary JSON-encoded data
    additional_data = models.TextField(blank=True)

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

    def for_experiment(self, experiment, **kwargs):
        return self.select_related('group', 'participant').filter(group__experiment=experiment, **kwargs)

# FIXME: deprecated, for backwards compatibility
    def by_experiment(self, experiment, **kwargs):
        return self.for_experiment(experiment, **kwargs)

    def get_relationship(self, participant, experiment):
        try:
            return self.select_related('group', 'participant__user').get(group__experiment=experiment, participant=participant)
        except ParticipantGroupRelationship.DoesNotExist:
            logger.warning("Participant %s does not belong to a group in %s", participant, experiment)
            return None

class ParticipantGroupRelationship(models.Model, DataValueMixin):
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

    def set_participant_ready(self, round_data=None):
        if round_data is None:
            round_data = self.current_round_data
        dv = self.get_data_value(parameter=get_participant_ready_parameter(), round_data=round_data)
        dv.submitted = True
        dv.boolean_value = True
        dv.save()
        return dv

    def get_round_configuration_value(self, **kwargs):
        return self.group.get_round_configuration_value(**kwargs)

    def __unicode__(self):
        return u"{0}: #{1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['group', 'participant_number']

class ParticipantRoundDataValueQuerySet(models.query.QuerySet):
    def for_participant(self, participant_group_relationship=None, **kwargs):
        if participant_group_relationship is None:
            raise ValueError("Must specify a participant_group_relationship keyword in this query")
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                'target_data_value__participant_group_relationship',
                ).filter(participant_group_relationship=participant_group_relationship, is_active=True, **kwargs).order_by('-date_created')

    def for_round(self, round_data=None, **kwargs):
        if round_data is None:
            raise ValueError("Must specify a round data object in this query")
        return self.select_related(
                'parameter',
                'participant_group_relationship__group'
                ).filter(round_data=round_data, is_active=True, **kwargs)

    def for_group(self, group=None, **kwargs):
        if group is None:
            raise ValueError("Must specify a group in this query")
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                'target_data_value__participant_group_relationship',
                ).filter(participant_group_relationship__group=group, is_active=True, **kwargs).order_by('-date_created')

class ParticipantRoundDataValue(ParameterizedValue):
    def __init__(self, *args, **kwargs):
        if 'round_data' not in kwargs and 'participant_group_relationship' in kwargs:
            kwargs['round_data'] = kwargs['participant_group_relationship'].current_round_data
        super(ParticipantRoundDataValue, self).__init__(*args, **kwargs)
    """
    Represents one data point collected for a given Participant in a given Round.
    """
    round_data = models.ForeignKey(RoundData, related_name='participant_data_value_set')
    participant_group_relationship = models.ForeignKey(ParticipantGroupRelationship, related_name='data_value_set')
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


class ChatMessageQuerySet(models.query.QuerySet):

    def for_experiment(self, experiment=None, **kwargs):
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                ).filter(parameter=get_chat_message_parameter(), round_data__experiment=experiment, **kwargs)

    def for_group(self, group=None, **kwargs):
        return self.select_related(
                'parameter',
                'participant_group_relationship__participant__user',
                'participant_group_relationship__group',
                ).filter(parameter=get_chat_message_parameter(), participant_group_relationship__group=group, **kwargs).order_by('-date_created')

    def message_all(self, experiment, message, round_data=None, **kwargs):
        if round_data is None:
            round_data = experiment.current_round_data
        for participant_group_relationship in ParticipantGroupRelationship.objects.for_experiment(experiment):
            ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                    string_value=message,
                    round_data=round_data)

class ChatMessage(ParticipantRoundDataValue):
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True, related_name='target_participant_chat_message_set')
    """ if set, this is a targeted message to another participant.  If null, broadcast message to the entire group """
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
        pgr = self.participant_group_relationship
        group = self.participant_group_relationship.group
        data.update(
                group_id=group.pk,
                group=unicode(group),
                participant_number=pgr.participant_number,
                event_type='chat',
                )
        return data

    def to_json(self, **kwargs):
        return dumps(self.to_dict())

    def __unicode__(self):
        """ return this participant's sequence number combined with the message """
        participant_number = self.participant_group_relationship.participant_number
        return u"{0}: {1}".format(participant_number, self.value)

    class Meta:
        ordering = ['-date_created']

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
        ordering = ['-date_created']

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
    invitation_text = models.TextField(blank=True)

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

''' parameter accessors '''
@simplecache
def get_chat_message_parameter():
    return Parameter.objects.get(name='chat_message', scope=Parameter.Scope.PARTICIPANT)

@simplecache
def get_comment_parameter():
    return Parameter.objects.get(name='comment', scope=Parameter.Scope.PARTICIPANT)

@simplecache
def get_like_parameter():
    return Parameter.objects.get(name='like', scope=Parameter.Scope.PARTICIPANT)

@simplecache
def get_participant_ready_parameter():
    return Parameter.objects.get(name='participant_ready', scope=Parameter.Scope.PARTICIPANT)


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

