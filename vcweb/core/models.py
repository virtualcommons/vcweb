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
from model_utils.managers import PassThroughManager
from string import Template

from vcweb.core import signals, simplecache, dumps

import base64
import email
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
    """
    Simple object wrapper that returns the wrapped value on any attribute reference
    """
    def __init__(self, value):
        self.value = value

    def __getattr__(self, name):
        return self.value

    def __str__(self):
        return '%s' % self.value

    def __unicode__(self):
        return u'%s' % self.value


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
            return DefaultValue(default)


class DataValueMixin(object):
    """
    Provides helper functions for model classes with related data value sets.

    Model classes using this mixin must have 'experiment' and 'data_value_set' attributes referring to the related
    Experiment and DataValue QuerySets, respectively.

    """
    def _criteria(self, parameter=None, parameter_name=None, round_data=None, active=True, **kwargs):
        return dict([('is_active', active),
                     ('parameter', parameter) if parameter else ('parameter__name', parameter_name),
                     ('round_data', self.experiment.current_round_data if round_data is None else round_data)],
                    **kwargs)

    def get_data_value(self, parameter=None, parameter_name=None, round_data=None, should_filter=False, default=None):
        if round_data is None:
            round_data = self.experiment.current_round_data
        criteria = self._criteria(parameter=parameter, parameter_name=parameter_name, round_data=round_data)
        data_value_set = self.data_value_set.select_related('parameter')
        data_value_class = data_value_set.model
        try:
            if should_filter:
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
            # no explicit round data to copy to, retrieve the next round data
            next_round_data, created = e.get_or_create_round_data(round_configuration=e.next_round,
                                                                  increment_repeated_round_sequence_number=True)
        for existing_dv in data_values:
            # setting the pk to None generates a new data value
            # http://stackoverflow.com/questions/12182657/copy-or-clone-an-object-instance-in-django-python
            existing_dv.pk = None
            existing_dv.round_data = next_round_data
            existing_dv.save()

    def set_data_value(self, parameter=None, value=None, round_data=None, **kwargs):
        if parameter is None or value is None:
            raise ValueError("need parameter and value to set")
        if round_data is None:
            round_data = self.experiment.current_round_data
        dv = self.get_data_value(round_data=round_data, parameter=parameter, **kwargs)
        dv.value = value
        dv.save()


class AutoDateTimeField(models.DateTimeField):
    def pre_save(self, model_instance, add):
        return datetime.now()


class NullCharField(models.CharField):
    description = "CharField that stores nulls in the db but returns ''"
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        kwargs['blank'] = True
        super(NullCharField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if isinstance(value, models.CharField):
            return value
        elif value is None:
            return u''
        else:
            return super(NullCharField, self).to_python(value)

    def get_prep_value(self, value):
        if value == '':
            return None
        else:
            return super(NullCharField, self).get_prep_value(value)

from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ["^vcweb\.core\.models\.AutoDateTimeField"])
add_introspection_rules([], ["^vcweb\.core\.models\.NullCharField"])


class ExperimentMetadataManager(models.Manager):

    def bookmarked(self, experimenter=None, **kwargs):
        bem_pks = BookmarkedExperimentMetadata.objects.filter(experimenter=experimenter).values_list('experiment_metadata', flat=True)
        for em in self.all():
            em.bookmarked = em.pk in bem_pks
            yield em

    def get_by_natural_key(self, key):
        return self.get(namespace=key)


class ExperimentMetadata(models.Model):
    """
    Represents the *type* of a given implemented Experiment, e.g., **forestry**, **lighter footprints**,
    **boundary effects**, or **irrigation**.

    This is distinct from a specific instance of a **forestry** or ** lighter footprints ** experiment, which represents
    a concrete experiment run, with a specific configuration, experimenter, etc.  Each experiment metadata app should
    define and add a single ExperimentMetadata record for the experiment type that it represents.
    """
    title = models.CharField(max_length=255)
    namespace_regex = re.compile(r'^(?:[/]?[a-z0-9_]+\/?)+$')
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=namespace_regex)])
    short_name = models.SlugField(max_length=32, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    about_url = models.URLField(null=True, blank=True)
    logo_url = models.URLField(null=True, blank=True)
    default_configuration = models.ForeignKey('ExperimentConfiguration', null=True, blank=True)

    objects = ExperimentMetadataManager()

    def to_dict(self, include_configurations=False, configurations=None, experimenter=None, **kwargs):
        data = {
            'pk': self.pk,
            'title': self.title,
            'namespace': self.namespace,
            'date_created': self.date_created,
            'description': self.description,
            'bookmarked': getattr(self, 'bookmarked', False)
        }
        if include_configurations:
            if configurations is None:
                configurations = ExperimentConfiguration.objects.select_related('creator').filter(experiment_metadata=self)
            data['configurations'] = [ec.to_dict() for ec in configurations]
        if experimenter is not None:
            data['bookmarked'] = BookmarkedExperimentMetadata.objects.filter(experiment_metadata=self, experimenter=experimenter).exists()
        return data

    def natural_key(self):
        return [self.namespace]

    def __unicode__(self):
        return u"%s /%s" % (self.title, self.namespace)

    class Meta:
        ordering = ['namespace', 'date_created']


class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    acronym = models.CharField(max_length=16, blank=True)
    description = models.TextField(blank=True)
    url = models.URLField(null=True, blank=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    cas_server_url = models.URLField(null=True, blank=True)

    def __unicode__(self):
        return self.name


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
    registration_email_subject = models.TextField(blank=True, help_text=_('subject header for email registrations'))
    invitation_text = models.TextField(blank=True, help_text=_('text to send out via email invitations'))
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    is_public = models.BooleanField(default=False)
    max_group_size = models.PositiveIntegerField(default=5)
    exchange_rate = models.DecimalField(null=True, blank=True, default=0.2, max_digits=6, decimal_places=2, help_text=_('The exchange rate of currency per in-game token, e.g., dollars per token'))
    treatment_id = models.CharField(blank=True, max_length=32, help_text=_('An alphanumeric ID that should be unique to the set of ExperimentConfigurations for a given ExperimentMetadata'))
    is_experimenter_driven = models.BooleanField(default=True)
    has_daily_rounds = models.BooleanField(default=False, help_text=_("This experiment configuration has rounds that start and end each day starting at midnight."))
    """
    Experimenter driven experiments have checkpoints where the experimenter
    needs to explicitly signal the system to move to the next round or stage.
    """
    cached_final_sequence_number = 0

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
    def total_number_of_rounds(self):
        number_of_rounds = self.round_configuration_set.count()
        repeating_rounds = self.round_configuration_set.filter(repeat__gt=0)
        number_of_rounds = number_of_rounds - repeating_rounds.count() + sum(repeating_rounds.values_list('repeat', flat=True))
        return number_of_rounds

    @property
    def final_sequence_number(self):
        # FIXME brittle with degenerate round configurations where the sequence numbers are out of sync and > count
        cfsn = self.cached_final_sequence_number
        if cfsn == 0:
            self.cached_final_sequence_number = cfsn = self.round_configuration_set.count()
        return cfsn

    @property
    def last_round_sequence_number(self):
        return self.round_configuration_set.aggregate(sequence_number=Max('sequence_number'))['sequence_number']

    @property
    def namespace(self):
        return self.experiment_metadata.namespace

    def clone(self, creator=None):
        """
        Returns a deep clone of this experiment configuration including all associated ExperimentParameterValues,
        RoundParameterValues, and RoundConfigurations
        """
        if creator is None:
            creator = self.creator
        ec = ExperimentConfiguration.objects.get(pk=self.pk)
        ec.pk = None
        ec.creator = creator
        ec.save()
        for epv in self.parameter_value_set.all():
            epv_clone = ExperimentParameterValue.objects.get(pk=epv.pk)
            epv_clone.pk = None
            epv_clone.experiment_configuration=ec
            epv.save()
        for rc in self.round_configuration_set.all():
            rc_clone = RoundConfiguration.objects.get(pk=rc.pk)
            rc_clone.pk = None
            rc_clone.experiment_configuration = ec
            rc_clone.save()
            for rpv in RoundParameterValue.objects.filter(round_configuration=rc):
                rpv.pk = None
                rpv.round_configuration = rc_clone
                rpv.save()
        return ec


    def to_dict(self, **kwargs):
        return {
            'pk': self.pk,
            'name': self.name,
            'treatment_id': self.treatment_id,
            'date_created': self.date_created.strftime("%m-%d-%Y %H:%M"),
            'creator': self.creator,
            'max_group_size': self.max_group_size,
            'is_experimenter_driven': self.is_experimenter_driven,
            'number_of_rounds': self.final_sequence_number
        }

    def serialize(self, output_format='xml', **kwargs):
        if self.round_configuration_set.exists():
            all_objects = []
            for rc in self.round_configuration_set.all():
                all_objects.append(rc)
                all_objects.extend(rc.parameter_value_set.all())
            all_objects.append(self)
            return serializers.serialize(output_format, all_objects, **kwargs)

    def __unicode__(self):
        return u"%s %s" % (self.name, self.experiment_metadata)

    class Meta:
        ordering = ['experiment_metadata', 'creator', '-date_created']


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
        return self.select_related('experimenter', 'experiment_metadata', 'experiment_configuration').filter(experimenter=experimenter, **kwargs)


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
    current_round_sequence_number = models.PositiveIntegerField(
        default=1,
        help_text=_("One-based sequence number used to identify which round the experiment is currently running"))
    """ A sequential sequence number, ranging from 1 to N to identify which round the experiment is currently running """
    current_repeated_round_sequence_number = models.PositiveIntegerField(
        default=0,
        help_text=_("The number of times this round has been repeated"))
    experimenter = models.ForeignKey(Experimenter)
    """ the user running this experiment """
    experiment_metadata = models.ForeignKey(ExperimentMetadata)
    """ the experiment metadata object that this experiment instance represents """
    experiment_configuration = models.ForeignKey(ExperimentConfiguration)
    """ the configuration parameters in use for this experiment run. """
    # FIXME: consider using django-model-utils but need to verify that it works with South - status = StatusField()
    status = models.CharField(max_length=32, choices=Status, default=Status.INACTIVE)
    """ the status of an experiment can be either INACTIVE, ACTIVE, ROUND_IN_PROGRESS, or COMPLETED """
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    # FIXME: inherit from TimeFramedModel instead?
    date_activated = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32, blank=True)
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Use with ExperimentConfiguration.has_daily_rounds set to true to signifythat the experiment should activate automatically on the specified date."))
    #end_date = models.DateField(null=True, blank=True, help_text=_("Used in conjuction with ExperimentConfiguration.has_daily_rounds set to true and signifies that the experiment should end at the specified time."))
    current_round_start_time = models.DateTimeField(null=True, blank=True)
    registration_email_subject = models.CharField(max_length=128, blank=True, help_text=_("email subject header on registration emails sent to a participant"))
    registration_email_text = models.TextField(blank=True)

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
    def end_date(self):
        if self.experiment_configuration.has_daily_rounds:
            return self.start_date + timedelta(self.number_of_rounds)
        logger.warn("Asking for end_date for non daily rounds experiment %s, returning start date %s instead", self,
                    self.start_date)
        return self.start_date

    @property
    def time_remaining(self):
        if self.is_timed_round:
            return max(0, self.current_round.duration - self.current_round_elapsed_time.seconds)
        return -1

    @property
    def time_remaining_label(self):
        tr = self.time_remaining
        if tr < 0:
            return "Untimed round, advance manually or via automated checkpointing"
        else:
            return tr

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
        cr = self.current_round
        if cr.is_repeating_round:
            return u"Round %s/%s (repeating round %d of %d)" % (self.current_round_sequence_number,
                                                                self.experiment_configuration.final_sequence_number,
                                                                self.current_repeated_round_sequence_number + 1,
                                                                cr.repeat)
        else:
            return u"Round %d of %d" % (cr.sequence_number, self.experiment_configuration.final_sequence_number)

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
        return self.group_cluster_set.filter(session_id=self.current_session_id)

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
    def number_of_rounds(self):
        return self.experiment_configuration.total_number_of_rounds

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

    # FIXME: consider caching this to avoid a query per invocation
    def get_round_data(self, round_configuration=None, previous_round=False, next_round=False):
        if round_configuration is None:
            round_configuration = self.current_round
        ps = dict(round_configuration=round_configuration)
        if round_configuration.is_repeating_round:
            current = self.current_repeated_round_sequence_number
            if previous_round:
                # XXX:  if we're looking for a previous repeating round and the current repeated
                # round sequence number is 0 we need to clamp the repeated round sequence number to N - 1 where N is the
                # number of repeats for that repeating round
                current = round_configuration.repeat - 1 if current == 0 else current - 1
            elif next_round:
                current += 1
            ps.update(repeating_round_sequence_number=current)
        return RoundData.objects.select_related('round_configuration').get(experiment=self, **ps)

    @property
    def playable_round_data(self):
        return self.round_data_set.select_related('experiment', 'round_configuration').filter(
            round_configuration__round_type__in=RoundConfiguration.PLAYABLE_ROUND_CONFIGURATIONS,
            round_configuration__sequence_number__lte=self.current_round_sequence_number)

    @property
    def all_chat_messages(self):
        return ChatMessage.objects.for_experiment(self)

    @property
    def should_repeat(self):
        cr = self.current_round
        return cr.is_repeating_round and self.current_repeated_round_sequence_number + 1 < cr.repeat

    @property
    def next_round(self):
        if not self.should_repeat and self.has_next_round:
            return self.get_round_configuration(self.current_round_sequence_number + 1)
        else:
            return self.current_round

    @property
    def previous_round(self):
        # FIXME: loop instead w/ mod?
        current_round = self.current_round
        if current_round.is_repeating_round and self.current_repeated_round_sequence_number > 0:
            return current_round
        else:
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
            ('group__session_id', session_id)
        ])
        return ParticipantGroupRelationship.objects.get(**criteria)

    def all_participants_have_submitted(self):
        return ParticipantRoundDataValue.objects.filter(submitted=False, round_data=self.current_round_data).count() == 0

    def get_registration_email_subject(self):
        subject = self.registration_email_subject
        if subject is None:
            subject = self.experiment_configuration.registration_email_subject
            if subject is None:
                subject = 'VCWEB experiment registration for %s' % self.display_name
        return subject

    def register_participants(self, users=None, emails=None, institution=None, password=None, sender=None, from_email=None):
        number_of_participants = self.participant_set.count()
        if number_of_participants > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, number_of_participants)
            return
        if users is None:
            users = []
            if emails is None:
                logger.warning("No users or emails supplied, aborting.")
                return
            for email_line in emails:
                if not email_line:
                    logger.debug("invalid participant data: %s", email_line)
                    continue
                # FIXME: parsing logic was already performed once in EmailListField.clean, redundant
                (full_name, email_address) = email.utils.parseaddr(email_line)
                # lowercase all usernames/email addresses internally and strip all whitespace
                email_address = email_address.lower().strip()
                full_name = full_name.strip()
                # crudely splitting last token as last_name and everything else as first_name
                (first_name, separator, last_name) = full_name.rpartition(' ')
                try:
                    u = User.objects.get(username=email_address)
                except User.DoesNotExist:
                    u = User.objects.create_user(username=email_address, email=email_address, password=password)
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
            # FIXME: instead of asking for the email suffix, just append the institution URL to keep it simpler?
            if institution and p.institution != institution:
                p.institution = institution
                p.save()
            per = ParticipantExperimentRelationship.objects.create(participant=p, experiment=self,
                                                                   created_by=self.experimenter.user)
            email_messages.append(self.create_registration_email(per, password=password, is_new_participant=created,
                                                                 sender=sender, from_email=from_email))
        if email_messages:
            mail.get_connection().send_messages(email_messages)

    def create_registration_email(self, participant_experiment_relationship, password='', sender=None, from_email=None, **kwargs):
        """
        Creates a registration email, sets a password for the given participant_experiment_relationship, and sends it to
        in plain text. Totally insecure but convenient for lowering barrier to participant registration.

        Override the email template by creating <experiment-namespace>/email/experiment-registration.(txt|html) templates
        """
        participant = participant_experiment_relationship.participant
        logger.debug("creating email for %s", participant)
        plaintext_template = select_template(['%s/email/experiment-registration.txt' % self.namespace,
                                              'email/experiment-registration.txt'])
        html_template = select_template(['%s/email/experiment-registration.html' % self.namespace,
                                         'email/experiment-registration.html'])
        user = participant.user
        if password is None or not password.strip():
            password = User.objects.make_random_password()
        # FIXME: resets existing user passwords, which might not be a good thing
        user.set_password(password)
        user.save()
        c = Context({
            'participant_experiment_relationship': participant_experiment_relationship,
            'participant': participant,
            'experiment': self,
            'password': password,
            'sender': sender
        })
        plaintext_content = plaintext_template.render(c)
        html_content = html_template.render(c)
        subject = self.get_registration_email_subject()
        experimenter_email = self.experimenter.email
        if from_email is None or not from_email.strip():
            from_email = experimenter_email
        to_address = [participant_experiment_relationship.participant.email]
        bcc_address = [experimenter_email]
        msg = EmailMultiAlternatives(subject, plaintext_content, from_email, to_address, bcc_address)
        msg.attach_alternative(html_content, "text/html")
        return msg

    def setup_test_participants(self, count=20, institution=None, email_suffix='mailinator.com', username_suffix='asu', password=None):
        if password is None:
            password = self.authentication_code
            if password is None:
                password = 'test'
        number_of_participants = self.participant_set.count()
        if number_of_participants > 0:
            logger.warning("This experiment %s already has %d participants - aborting", self, number_of_participants)
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

    def initialize_data_values(self, group_parameters=[], participant_parameters=[], group_cluster_parameters=[], round_data=None, defaults={}):
        """
        FIXME: needs refactoring, replace get_or_create with creates and separate initialization of data values from copy_to_next_round semantics
        Issues:
            Make it simple for experimenters/experiments to signal "I have these data values to initialize at the start of each round"
            Overly complex logic, possible danger to use empty lists as initial keyword args but we only iterate over them (e.g., http://effbot.org/zone/default-values.htm)
            get_or_create logic can create degenerate data (duplicate group round data values for instance)
        """
        if round_data is None:
            round_data = self.current_round_data
        round_configuration = round_data.round_configuration
        if not round_configuration.initialize_data_values:
            logger.debug("Aborting, round configuration isn't set to initialize data values")
            return
        elif round_configuration.is_repeating_round and self.current_repeated_round_sequence_number > 0:
            logger.debug("ignoring for repeating round %d", self.current_repeated_round_sequence_number)
            return

        logger.debug("round data %s initializing [participant params: %s]  [group parameters: %s] [group_cluster_parameters: %s] ", round_data,
                     participant_parameters, group_parameters, group_cluster_parameters)
        parameter_defaults = defaultdict(dict)
        # defaults map parameter model instances to their default initial value, e.g.,
        # { footprint-level-parameter: 1, resource-level-parameter: 100 }
        for parameter in itertools.chain(participant_parameters, group_parameters, group_cluster_parameters):
            if parameter in defaults:
                parameter_defaults[parameter] = { parameter.value_field_name: defaults[parameter] }
        logger.debug("parameter default values: %s", parameter_defaults)
        # create group cluster parameter data values
        if group_cluster_parameters:
            for group_cluster in self.active_group_clusters:
                for parameter in group_cluster_parameters:
                    gcdv, created = GroupClusterDataValue.objects.get_or_create(round_data=round_data,
                                                                                parameter=parameter,
                                                                                group_cluster=group_cluster,
                                                                                defaults=parameter_defaults[parameter])
                    logger.debug("gcdv: %s (%s)", gcdv, created)
        for group in self.groups:
            for parameter in group_parameters:
                group_data_value, created = GroupRoundDataValue.objects.get_or_create(round_data=round_data,
                                                                                      group=group, parameter=parameter,
                                                                                      defaults=parameter_defaults[parameter])
                logger.debug("grdv: %s (%s)", group_data_value, created)
            if participant_parameters:
                for pgr in group.participant_group_relationship_set.all():
                    for parameter in participant_parameters:
                        participant_data_value, created = round_data.participant_data_value_set.get_or_create(
                            participant_group_relationship=pgr,
                            parameter=parameter,
                            defaults=parameter_defaults[parameter])
                        logger.debug("prdv: %s (%s)", participant_data_value, created)

    def log(self, log_message, *args, **kwargs):
        if log_message:
            log_message = "%s: %s" % (self, log_message)
            logger.debug(log_message, *args)
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
            ParticipantExperimentRelationship.objects.create(participant=participant,
                                                             experiment=self,
                                                             created_by=participant.user)
        pgrs = ParticipantGroupRelationship.objects.filter(group__experiment=self, participant=participant)
        if current_group is None:
            # try to add them to the last group in group_set with the same session id
            session_id_groups = self.group_set.filter(session_id=session_id)
            if session_id_groups:
                current_group = session_id_groups.reverse()[0]
            number_of_groups = self.group_set.count()
            if current_group is None or number_of_groups == 0:
                # create a new group
                current_group = self.group_set.create(number=number_of_groups,
                                                      max_size=max_group_size,
                                                      session_id=session_id)

        if pgrs.exists():
            # ensure that any existing group that this participant is in has a different session id from this group
            for pgr in pgrs:
                if pgr.group.session_id == current_group.session_id:
                    logger.error("Participant %s already in a group %s with the same session id, not adding them to %s",
                                 participant, pgr.group, current_group)
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
        if gs.exists():
            """
            groups already exist, preserve or delete them
            FIXME: would be safer to always preserve as it doesn't carry any risk of data loss, could autogenerate
            a session id if one isn't found.
            """
            if preserve_existing_groups:
                logger.debug("preserving existing groups")
                # initialize session_id to round configuration session_id if unset. if none can be found abort
                if not session_id:
                    round_configuration = self.current_round
                    session_id = round_configuration.session_id
                    if not session_id:
                        logger.error("Cannot create a new set of groups because no session id has been set on %s.",
                                     round_configuration)
                        raise ValueError("Cannot allocate new groups and preserve existing groups without an appropriate session id set on this round configuration %s" % round_configuration)
            else:
                logger.debug("deleting old groups")
                # FIXME: fairly expensive operation to log all group members
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
                logger.error("cannot create clusters of size %s, we have %s groups which isn't evenly divisible.",
                             group_cluster_size, len(groups))
                return
            random.shuffle(groups)
            gc = GroupCluster.objects.create(session_id=session_id, experiment=self)
            for group in groups:
                if gc.group_relationship_set.count() == group_cluster_size:
                    # if this group cluster is full, create a new one
                    gc = GroupCluster.objects.create(session_id=session_id, experiment=self)
                # then add group to the cluster
                gc.add(group)

    def get_round_configuration(self, sequence_number):
        return RoundConfiguration.objects.get(experiment_configuration__experiment=self, sequence_number=sequence_number)

    ALLOWED_ACTIONS = ('advance_to_next_round', 'end_round', 'start_round', 'move_to_previous_round', 'activate',
                       'deactivate', 'complete', 'restart_round', 'restart', 'clone')

    def invoke(self, action_name, experimenter=None):
        if action_name in Experiment.ALLOWED_ACTIONS:
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
            return None
        return self.start_round()

    def get_or_create_round_data(self, round_configuration=None, increment_repeated_round_sequence_number=False):
        current_round = self.current_round
        if round_configuration is None:
            round_configuration = current_round
        ps = dict(round_configuration=round_configuration)
        if round_configuration.is_repeating_round:
            same_repeating_round = self.current_round == round_configuration
            # initialize repeating round sequence number as 0
            rrsn = 0
            # if the incoming round configuration is the same as the current round set to the
            # current_repeated_round_sequence_number. we only explicitly increment the repeated round sequence number
            # when invoked at the end of a round and copying data parameters from the current round to the next. I.e.,
            # copy_to_next_round invokes get_or_create_round_data(..., increment_repeated_round_sequence_number=True)
            if same_repeating_round:
                rrsn = self.current_repeated_round_sequence_number
                if increment_repeated_round_sequence_number:
                    rrsn += 1
            ps['repeating_round_sequence_number'] = rrsn
        round_data, created = self.round_data_set.get_or_create(**ps)
        logger.debug("generated round data %s with criteria %s", round_data, ps)
        if self.experiment_configuration.is_experimenter_driven:
            # create participant ready data values for every round in experimenter driven experiments
            logger.debug("creating participant ready participant round data values for experimenter driven experiment")
            # FIXME: use bulk_create for this?
            # see https://docs.djangoproject.com/en/dev/ref/models/querysets/#bulk-create
            for pgr in self.participant_group_relationships:
                pgr.data_value_set.get_or_create(
                    parameter=get_participant_ready_parameter(),
                    round_data=round_data,
                    defaults={'boolean_value': False})
        if not created:
            logger.debug("round data already created: %s", round_data)
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
        signal_tuple = signals.round_started.send_robust(sender, experiment=self, time=datetime.now(),
                                                         round_configuration=current_round_configuration)
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
        # reset all survey completed flags on participant group relationships within this experiment
        self._reset_survey_completed_flags()
        self.log('Ending round with elapsed time %s' % self.current_round_elapsed_time)
        sender = intern(self.experiment_metadata.namespace.encode('utf8')) if sender is None else sender
        #sender = self.namespace.encode('utf-8')
        logger.debug("about to send round ended signal with sender %s", sender)
        signal_tuple = signals.round_ended.send_robust(sender, experiment=self, round_configuration=self.current_round)
        self._check_signal_result(signal_tuple)
        return signal_tuple

    def activate(self):
        if self.is_archived:
            logger.debug("ignoring request to activate archived experiment, it would wipe existing data.")
        elif not self.is_active:
            self.allocate_groups()
            self.status = Experiment.Status.ACTIVE
            self.date_activated = datetime.now()
            self.start_round()
        return self

    def restart(self):
        self.log("Restarting experiment entirely from the first round and clearing out all existing data.")
        self.deactivate()
        self.activate()
        self.start_round()

    def restart_round(self):
        self.end_round()
        self.start_round()

    def complete(self):
        if self.is_round_in_progress:
            self.end_round()
        self.log("Marking as COMPLETED")
        self.status = Experiment.Status.COMPLETED
        self.save()

    def deactivate(self):
        self.log("Deactivating experiment, deleting all data and flagging as inactive.")
        self.status = Experiment.Status.INACTIVE
        self.round_data_set.all().delete()
        self.current_round_sequence_number = 1
        self.current_repeated_round_sequence_number = 0
        self.save()

    def clear_participants(self):
        logger.debug("clearing all participants for experiment %s", self)
        ParticipantExperimentRelationship.objects.filter(experiment=self).delete()
        ParticipantGroupRelationship.objects.filter(group__experiment=self).delete()
        self.deactivate()

    def check_elapsed_time(self):
        if self.is_timed_round and self.is_time_expired:
            self.end_round()

    def all_round_data(self):
        # FIXME: figure out a better way to convert these to json that doesn't involve manual remapping of attribute
        # names or be consistent so that things on the client side are named the same as the server side
        all_round_data = []
        for round_data in self.round_data_set.select_related('round_configuration').reverse():
            rc = round_data.round_configuration
            all_round_data.append({
                'pk': round_data.pk,
                'roundDataId': "roundData_%s" % round_data.pk,
                'experimenterNotes': round_data.experimenter_notes,
                'roundType': rc.get_round_type_display(),
                'roundNumber': round_data.round_number,
                # empty stubs to be loaded dynamically
                'groupDataValues': [],
                'participantDataValues': []
            })
        return all_round_data

    def to_dict(self, include_round_data=False, default_value_dict=None, attrs=None, *args, **kwargs):
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
            'exchangeRate': float(self.experiment_configuration.exchange_rate),
            'readyParticipants': self.number_of_ready_participants,
            'status': self.status,
            'pk': self.pk
        })
        if include_round_data:
            # XXX: stubs for round data
            experiment_dict['allRoundData'] = self.all_round_data()
            experiment_dict['chatMessages'] = [chat_message.to_dict() for chat_message in self.all_chat_messages]
            experiment_dict['messages'] = map(str, self.activity_log_set.order_by('-date_created')[:100])
            experiment_dict['experimenterNotes'] = self.current_round_data.experimenter_notes if self.is_round_in_progress else ''
            experiment_dict['groups'] = [group.to_dict() for group in self.groups]
        # FIXME: intended to provide some way to include more experiment attributes at invocation time, may remove
        if attrs:
            experiment_dict.update([(attr, getattr(self, attr, None)) for attr in attrs])
        return experiment_dict

    def as_dict(self, *args, **kwargs):
        return self.to_dict(*args, **kwargs)

    def to_json(self, include_round_data=False, *args, **kwargs):
        return dumps(self.to_dict(include_round_data, *args, **kwargs))

    def clone(self, experimenter=None):
        """ returns a fresh copy of this experiment with an optional new experimenter """
        if not experimenter:
            experimenter = self.experimenter
        return Experiment.objects.create(experimenter=experimenter,
                                         authentication_code=self.authentication_code,
                                         experiment_metadata=self.experiment_metadata,
                                         experiment_configuration=self.experiment_configuration,
                                         duration=self.duration,
                                         tick_duration=self.tick_duration,
                                         status=Experiment.Status.INACTIVE)

    def _reset_survey_completed_flags(self):
        ParticipantGroupRelationship.objects.for_experiment(self).update(survey_completed=False)

    def __unicode__(self):
        return u"%s #%s | %s" % (self.experiment_configuration, self.pk, self.experimenter)

    class Meta:
        ordering = ['date_created', 'status']


class RoundConfiguration(models.Model, ParameterValueMixin):
    # FIXME: refactor this into a single data structure
    # maps round type name to (description, default_template_filename)
    ROUND_TYPES_DICT = dict(
        WELCOME=(_('Initial welcome page'), 'welcome.html'),
        GENERAL_INSTRUCTIONS=(_('General introduction to the experiment'), 'general-instructions.html'),
        REGULAR=(_('Regular experiment round'), 'participate.html'),
        CHAT=(_('Chat round'), 'chat.html'),
        DEBRIEFING=(_('Debriefing round'), 'debriefing.html'),
        INSTRUCTIONS=(_('Instructions round'), 'instructions.html'),
        PRACTICE=(_('Practice round'), 'practice.html'),
        QUIZ=(_('Quiz round'), 'quiz.html'))
    ROUND_TYPES = (CHAT, DEBRIEFING, GENERAL_INSTRUCTIONS, INSTRUCTIONS, PRACTICE, QUIZ, REGULAR, WELCOME) = sorted(ROUND_TYPES_DICT.keys())
    RoundType = Choices(*[(round_type, ROUND_TYPES_DICT[round_type][0]) for round_type in ROUND_TYPES])
    PLAYABLE_ROUND_CONFIGURATIONS = (RoundType.PRACTICE, RoundType.REGULAR)

    experiment_configuration = models.ForeignKey(ExperimentConfiguration, related_name='round_configuration_set')
    sequence_number = models.PositiveIntegerField(
        help_text=_('Determines the ordering of the rounds in an experiment in ascending order, e.g., 1,2,3,4,5'))
    display_number = models.PositiveIntegerField(
        default=0,
        help_text=_('Display round number, defaults to sequence_number if 0.'))
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = AutoDateTimeField(default=datetime.now)
    duration = models.PositiveIntegerField(
        default=0,
        help_text=_('Duration in seconds. 0 signifies an untimed round only advanced by an experimenter.'))
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
    """ external survey url for qualtrics integration """
    chat_enabled = models.BooleanField(default=False, help_text=_("Enable in-round communication"))
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
    initialize_data_values = models.BooleanField(default=False, help_text=_("Re-initialize all group and participant parameters at the start of this round.  "))

    @property
    def template_name(self):
        return self.template_id if self.template_id else self.round_type

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
        return Template(template_string).substitute(kwargs,
                                                    round_number=self.display_number,
                                                    participant_id=participant_id)

    @property
    def display_label(self):
        return u"Round %d" % self.round_number if self.is_regular_round else self.get_round_type_display()

    @property
    def sequence_label(self):
        if self.is_repeating_round:
            return u"%d of %d [x %d]" % (self.sequence_number, self.experiment_configuration.final_sequence_number, self.repeat)
        else:
            return u"%d of %d" % (self.sequence_number, self.experiment_configuration.final_sequence_number)

    def __unicode__(self):
        return u"%s %s %s %s" % (self.get_round_type_display(), self.sequence_label, self.experiment_configuration,
                                   self.session_id)

    class Meta:
        ordering = [ 'experiment_configuration', 'sequence_number', 'date_created' ]


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


def _fk_converter(fk_cls):
    def converter(value):
        if isinstance(value, (int, long)):
            return value
        elif isinstance(value, fk_cls):
            return value.pk
        raise ValueError("can only convert integers or %s - received %s" % (fk_cls, value))
    return converter


class Parameter(models.Model):
    ParameterType = Choices(
        ('int', 'Integer value'),
        ('string', 'String value'),
        ('foreignkey', 'Foreign key'),
        ('float', 'Floating-point number'),
        ('boolean', 'Boolean value (true/false)'),
        ('enum', 'Enumeration'))
    Scope = Choices(
        ('round', 'ROUND', 'Round configuration data applicable to all groups for a given round'),
        ('experiment', 'EXPERIMENT', 'Experiment configuration data relevant to the entire experiment'),
        ('group', 'GROUP', 'Group data for a given group in a given round'),
        ('group_cluster', 'GROUP_CLUSTER', 'Group cluster data for a given group cluster in a given round'),
        ('participant', 'PARTICIPANT', 'Participant data for a given participant in a given round'))
    # FIXME: arcane, used to provide sane default values for each parameter type when the parameter is null
    NONE_VALUES_DICT = dict(map(lambda x,y: (x[0], y), ParameterType, [0, '', -1, 0.0, False, None]))
    CONVERTERS = {
        'int': int,
        'string': str,
        'float': float,
        'foreignkey': _fk_converter,
        'boolean': lambda x: bool(x) and str(x).lower() != 'false',
        'enum': str
    }
    """
    all converters are one-arg functions that convert string input into the appropriate data type.
    they expect valid string data and will throw ValueErrors on invalid input like None.
    """
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
    Base type for GroupRoundDataValue and ParticipantRoundDataValues
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

    def update(self, val, submitted=None):
        self.value = val
        if submitted is not None: self.submitted = submitted
        self.save()

    def update_str(self, str_value, submitted=None):
        self.string_value = str_value
        if submitted is not None: self.submitted = submitted
        self.save()

    def update_int(self, integer_value, submitted=None):
        self.int_value = integer_value
        if submitted is not None: self.submitted = submitted
        self.save()

    def update_boolean(self, boolean_value, submitted=False):
        self.boolean_value = boolean_value
        if submitted is not None: self.submitted = submitted
        self.save()

    def to_dict(self, cacheable=False, **kwargs):
        p = self.parameter
        return {
            'pk': self.pk,
            'date_created': self.date_created,
            'short_date_created': self.date_created.strftime('%I:%M:%S'),
            'parameter_name': p.name,
            'parameter_label': p.label,
            'value': unicode(self.cached_value if cacheable else self.value)
        }

    def __unicode__(self):
        return u"Data value: [parameter {0}, value {1}], recorded at {2}".format(self.parameter, self.value, self.date_created)

    class Meta:
        abstract = True


class ExperimentParameterValue(ParameterizedValue):
    """ Represents an experiment configuration parameter applicable across the entire experiment """
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

    class Meta:
        ordering = [ 'round_configuration', 'parameter', 'date_created' ]


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
        # FIXME: currently only assumes single paired relationships
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
        criteria = self._criteria(**kwargs)
        try:
            return self.data_value_set.filter(**criteria).exists()
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

    def _criteria(self, parameter=None, parameter_name=None, round_data=None, **kwargs):
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
        criteria = self._criteria(participant_group_relationship__group=self, **kwargs)
        return ParticipantRoundDataValue.objects.filter(**criteria)

    def create_next_group(self):
        return Group.objects.create(number=self.number + 1, max_size=self.max_size, experiment=self.experiment,
                                    session_id=self.session_id)

    def add_participant(self, participant=None):
        """
        Adds the given participant to this group or a new group if this group is is_full.
        Returns the participant group relationship created by adding this participant or None if the participant is invalid.
        """
        if participant is None:
            logger.warning("Trying to add invalid participant %s to group %s", participant, self)
            return None
        # add the participant to this group if there is room, otherwise create and add to a fresh group
        group = self if self.is_open else self.create_next_group()
        logger.debug("adding participant %s to group %s", participant, group)
        pgr = ParticipantGroupRelationship.objects.create(participant=participant,
                                                          group=group,
                                                          round_joined=self.experiment.current_round,
                                                          participant_number=group.size + 1)
        signals.participant_added.send_robust(self, experiment=self.experiment, time=datetime.now(),
                                              participant_group_relationship=pgr)
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
    repeating_round_sequence_number = models.PositiveIntegerField(
        default=0,
        help_text=_("Sequence number used to disambiguate round data in repeating rounds"))
    elapsed_time = models.PositiveIntegerField(default=0)
    experimenter_notes = models.TextField(blank=True)

    @property
    def round_number(self):
        rc = self.round_configuration
        round_number = rc.round_number
        if rc.is_repeating_round:
            return "%s.%s" % (round_number, self.repeating_round_sequence_number + 1)
        else:
            return round_number

    @property
    def session_id(self):
        return self.round_configuration.session_id

    def __unicode__(self):
        if self.round_configuration.is_repeating_round:
            return u"Repeating round data %s.%s" % (self.round_configuration.sequence_number, self.repeating_round_sequence_number)
        return u"Round data %s" % self.round_configuration.sequence_label

    class Meta:
        ordering = [ 'round_configuration', 'repeating_round_sequence_number' ]
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
    CLASS_CHOICES = Choices('Freshman', 'Sophomore', 'Junior', 'Senior', 'Graduate', 'Other')
    can_receive_invitations = models.BooleanField(default=False)
    groups = models.ManyToManyField(Group, through='ParticipantGroupRelationship', related_name='participant_set')
    experiments = models.ManyToManyField(Experiment, through='ParticipantExperimentRelationship', related_name='participant_set')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    birthdate = models.DateField(null=True, blank=True)
    major = models.CharField(max_length=64, blank=True)
    class_status = models.CharField(max_length=32, choices=CLASS_CHOICES, blank=True)
    address = models.ForeignKey(Address, null=True, blank=True)
    institution_username = NullCharField(max_length=64, unique=True, help_text=_('Unique institution-specific username, e.g., ASURITE, IU Network ID'))

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
# FIXME: deprecate & remove
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
    survey_completed = models.BooleanField(default=False)

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
            'target_data_value__participant_group_relationship'
        ).filter(participant_group_relationship=participant_group_relationship,
                 is_active=True,
                 **kwargs).order_by('-date_created')

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
            'target_data_value__participant_group_relationship'
        ).filter(participant_group_relationship__group=group, is_active=True, **kwargs).order_by('-date_created')


class ParticipantRoundDataValue(ParameterizedValue):
    """
    Represents a single data point for a given Participant in a given Round.
    """
    def __init__(self, *args, **kwargs):
        if 'round_data' not in kwargs and 'participant_group_relationship' in kwargs:
            kwargs['round_data'] = kwargs['participant_group_relationship'].current_round_data
        super(ParticipantRoundDataValue, self).__init__(*args, **kwargs)

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
        # unique_together = (('parameter', 'participant_group_relationship'),)


class ChatMessageQuerySet(models.query.QuerySet):

    def for_experiment(self, experiment=None, **kwargs):
        return self.select_related(
            'parameter',
            'participant_group_relationship__participant__user',
            'participant_group_relationship__group'
        ).filter(parameter=get_chat_message_parameter(), round_data__experiment=experiment, **kwargs)

    def for_group(self, group=None, **kwargs):
        return self.select_related(
            'parameter',
            'participant_group_relationship__participant__user',
            'participant_group_relationship__group'
        ).filter(parameter=get_chat_message_parameter(), participant_group_relationship__group=group, **kwargs).order_by('-date_created')

    def message_all(self, experiment, message, round_data=None, **kwargs):
        if round_data is None:
            round_data = experiment.current_round_data
        for participant_group_relationship in experiment.participant_group_relationships:
            ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                                       string_value=message,
                                       round_data=round_data)


class ChatMessage(ParticipantRoundDataValue):
    target_participant = models.ForeignKey(ParticipantGroupRelationship, null=True, blank=True,
                                           related_name='target_participant_chat_message_set')
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
            event_type='chat'
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
    """
    Represents an actual experiment session that needs to take place at a certain place and time
    """
    experiment_metadata = models.ForeignKey(ExperimentMetadata, related_name='experiment_session_set')
    date_created = models.DateTimeField(default=datetime.now)
    scheduled_date = models.DateTimeField()
    scheduled_end_date = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=20)
    creator = models.ForeignKey(User, related_name='experiment_session_set')
# wire up with autocomplete
    location = models.CharField(max_length=128, blank=True, help_text=_('Location where this experiment session will be held.'))
# FIXME: consider placing this somewhere more re-usable, or allow use of ExperimentConfiguration.invitation_text as a fallback
    invitation_text = models.TextField(blank=True)


class Invitation(models.Model):
    participant = models.ForeignKey(Participant)
    experiment_session = models.ForeignKey(ExperimentSession)
    date_created = models.DateTimeField(default=datetime.now)
    sender = models.ForeignKey(User)


class ParticipantSignupQuerySet(models.query.QuerySet):
    
    def _experiment_metadata_criteria(self, criteria, experiment_metadata=None, experiment_metadata_pk=None):
        if experiment_metadata is not None:
            criteria['invitation__experiment_session__experiment_metadata'] = experiment_metadata
        elif experiment_metadata_pk is not None:
            criteria['invitation__experiment_session__experiment_metadata__pk'] = experiment_metadata_pk
        return criteria

    def registered(self, **kwargs):
        criteria = self._experiment_metadata_criteria({ 'attendance__in': (ParticipantSignup.ATTENDANCE.participated, ParticipantSignup.ATTENDANCE.registered)}, **kwargs)
        return self.filter(**criteria)

    def participated(self, **kwargs):
        criteria = self._experiment_metadata_criteria({ 'attendance': ParticipantSignup.ATTENDANCE.participated }, **kwargs)
        return self.filter(**criteria)


class ParticipantSignup(models.Model):
    ATTENDANCE = Choices((0, 'participated', _('participated')), (1, 'discharged', _('turned away')), (2, 'absent', _('absent')), (3, 'registered', _('signed up')))
    """ Provides participated, discharged, absent, and initial attendance enum values """
    invitation = models.ForeignKey(Invitation, related_name='signup_set')
    date_created = models.DateTimeField(default=datetime.now)
    attendance = models.PositiveIntegerField(max_length=1, choices=ATTENDANCE, default=ATTENDANCE.registered)

    objects = PassThroughManager.for_queryset_class(ParticipantSignupQuerySet)()

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


@receiver(signals.system_daily_tick)
def update_daily_experiments(sender, time=None, start=None, **kwargs):
    """
    signal handler for activating daily experiments
    """
    today = datetime.today().date()
    # first advance all active daily round experiments to the next round or complete them if they've hit completion
    active_daily_experiments = Experiment.objects.active(experiment_configuration__has_daily_rounds=True)
    for e in active_daily_experiments:
        # FIXME: check for none result and end the experiment?
        if e.has_next_round:
            e.advance_to_next_round()
        else:
            e.complete()
    # next activate inactive daily experiments that need to be activated, this MUST happen after advancing the inactive
    # experiments, otherwise we'll advance the just-activated experiments.
    inactive_daily_experiments = Experiment.objects.inactive(experiment_configuration__has_daily_rounds=True)
    for e in inactive_daily_experiments:
        if e.start_date == today:
            logger.debug("activating experiment %s with start date of %s", e, e.start_date)
            e.activate()


def reset_password(email, from_email='vcweb@asu.edu', template='registration/password_reset_email.html'):
    """
    Reset the password for all (active) users with given E-Mail address
    """
    form = PasswordResetForm({'email': email, })
    return form.save(from_email=from_email, email_template_name=template)

