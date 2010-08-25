from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from vcweb import settings
from vcweb.core import signals
import datetime
import hashlib
import logging
import random
import re

SHA1_RE = re.compile('^[a-f0-9]{40}$')

logger = logging.getLogger('vcweb.core.models')

def second_tick_handler(sender, time=None, **kwargs):
    logger.debug("handling second tick signal at %s" % time)


signals.second_tick.connect(second_tick_handler, sender=None)

# FIXME: separate accounts / registration / experimenter / participant app from the core app

# registration manager included / forked from http://bitbucket.org/ubernostrum/django-registration/
class RegistrationManager(models.Manager):
    """
    Custom manager for the ``RegistrationProfile`` model.
    
    The methods defined here provide shortcuts for account creation
    and activation (including generation and emailing of activation
    keys), and for cleaning out expired inactive accounts.
    
    """
    def activate_user(self, activation_key):
        """
        Validate an activation key and activate the corresponding
        ``User`` if valid.
        
        If the key is valid and has not expired, return the ``User``
        after activating.
        
        If the key is not valid or has expired, return ``False``.
        
        If the key is valid but the ``User`` is already active,
        return ``False``.
        
        To prevent reactivation of an account which has been
        deactivated by site administrators, the activation key is
        reset to the string constant ``RegistrationProfile.ACTIVATED``
        after successful activation.

        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            if not profile.activation_key_expired():
                user = profile.user
                user.is_active = True
                user.save()
                profile.activation_key = self.model.ACTIVATED
                profile.save()
                return user
        return False

    def create_inactive_user(self, username, email, password,
                             site, send_email=True):
        """
        Create a new, inactive ``User``, generate a
        ``RegistrationProfile`` and email its activation key to the
        ``User``, returning the new ``User``.

        By default, an activation email will be sent to the new
        user. To disable this, pass ``send_email=False``.
        
        """
        new_user = User.objects.create_user(username, email, password)
        new_user.is_active = False
        new_user.save()

        registration_profile = self.create_profile(new_user)

        if send_email:
            registration_profile.send_activation_email(site)

        return new_user
    create_inactive_user = transaction.commit_on_success(create_inactive_user)

    def create_profile(self, user):
        """
        Create a ``RegistrationProfile`` for a given
        ``User``, and return the ``RegistrationProfile``.
        
        The activation key for the ``RegistrationProfile`` will be a
        SHA1 hash, generated from a combination of the ``User``'s
        username and a random salt.
        
        """

        salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
        activation_key = hashlib.sha1(salt + user.username).hexdigest()
        return self.create(user=user,
                           activation_key=activation_key)

    def delete_expired_users(self):
        """
        Remove expired instances of ``RegistrationProfile`` and their
        associated ``User``s.
        
        Accounts to be deleted are identified by searching for
        instances of ``RegistrationProfile`` with expired activation
        keys, and then checking to see if their associated ``User``
        instances have the field ``is_active`` set to ``False``; any
        ``User`` who is both inactive and has an expired activation
        key will be deleted.
        
        It is recommended that this method be executed regularly as
        part of your routine site maintenance; this application
        provides a custom management command which will call this
        method, accessible as ``manage.py cleanupregistration``.
        
        Regularly clearing out accounts which have never been
        activated serves two useful purposes:
        
        1. It alleviates the ocasional need to reset a
           ``RegistrationProfile`` and/or re-send an activation email
           when a user does not receive or does not act upon the
           initial activation email; since the account will be
           deleted, the user will be able to simply re-register and
           receive a new activation key.
        
        2. It prevents the possibility of a malicious user registering
           one or more accounts and never activating them (thus
           denying the use of those usernames to anyone else); since
           those accounts will be deleted, the usernames will become
           available for use again.
        
        If you have a troublesome ``User`` and wish to disable their
        account while keeping it in the database, simply delete the
        associated ``RegistrationProfile``; an inactive ``User`` which
        does not have an associated ``RegistrationProfile`` will not
        be deleted.
        
        """
        for profile in self.all():
            if profile.activation_key_expired():
                user = profile.user
                if not user.is_active:
                    user.delete()


class RegistrationProfile(models.Model):
    """
    A simple profile which stores an activation key for use during
    user account registration.
    
    Generally, you will not want to interact directly with instances
    of this model; the provided manager includes methods
    for creating and activating new accounts, as well as for cleaning
    out accounts which have never been activated.
    
    While it is possible to use this model as the value of the
    ``AUTH_PROFILE_MODULE`` setting, it's not recommended that you do
    so. This model's sole purpose is to store data temporarily during
    account registration and activation.
    
    """
    ACTIVATED = u"ALREADY_ACTIVATED"

    user = models.ForeignKey(User, unique=True, verbose_name=_('user'))
    activation_key = models.CharField(_('activation key'), max_length=40)

    objects = RegistrationManager()

    class Meta:
        verbose_name = _('registration profile')
        verbose_name_plural = _('registration profiles')

    def __unicode__(self):
        return u"Registration information for %s" % self.user

    def activation_key_expired(self):
        """
        Determine whether this ``RegistrationProfile``'s activation
        key has expired, returning a boolean -- ``True`` if the key
        has expired.
        
        Key expiration is determined by a two-step process:
        
        1. If the user has already activated, the key will have been
           reset to the string constant ``ACTIVATED``. Re-activating
           is not permitted, and so this method returns ``True`` in
           this case.

        2. Otherwise, the date the user signed up is incremented by
           the number of days specified in the setting
           ``ACCOUNT_ACTIVATION_DAYS`` (which should be the number of
           days after signup during which a user is allowed to
           activate their account); if the result is less than or
           equal to the current date, the key has expired and this
           method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_ACTIVATION_DAYS)
        return self.activation_key == self.ACTIVATED or \
               (self.user.date_joined + expiration_date <= datetime.datetime.now())
    activation_key_expired.boolean = True

    def send_activation_email(self, site):
        """
        Send an activation email to the user associated with this
        ``RegistrationProfile``.
        
        The activation email will make use of two templates:

        ``registration/activation_email_subject.txt``
            This template will be used for the subject line of the
            email. Because it is used as the subject line of an email,
            this template's output **must** be only a single line of
            text; output longer than one line will be forcibly joined
            into only a single line.

        ``registration/activation_email.txt``
            This template will be used for the body of the email.

        These templates will each receive the following context
        variables:

        ``activation_key``
            The activation key for the new account.

        ``expiration_days``
            The number of days remaining during which the account may
            be activated.

        ``site``
            An object representing the site on which the user
            registered; depending on whether ``django.contrib.sites``
            is installed, this may be an instance of either
            ``django.contrib.sites.models.Site`` (if the sites
            application is installed) or
            ``django.contrib.sites.models.RequestSite`` (if
            not). Consult the documentation for the Django sites
            framework for details regarding these objects' interfaces.

        """
        ctx_dict = { 'activation_key': self.activation_key,
                     'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS,
                     'site': site }
        subject = render_to_string('registration/activation_email_subject.txt',
                                   ctx_dict)
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())

        message = render_to_string('registration/activation_email.txt',
                                   ctx_dict)

        self.user.email_user(subject, message, settings.DEFAULT_FROM_EMAIL)

# manager classes
class GameMetadataManager(models.Manager):

    def get_by_natural_key(self, key):
        return self.get(namespace=key)


# Create your models here.
class GameMetadata(models.Model):
    title = models.CharField(max_length=255)
    # the URL namespace that this game will occupy
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=r'^\w+$'), ])
    description = models.TextField(null=True, blank=True)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    about_url = models.URLField(null=True, blank=True, verify_exists=True)
    logo_url = models.URLField(null=True, blank=True, verify_exists=True)
    default_game_configuration = models.ForeignKey('GameConfiguration', null=True, blank=True)

    objects = GameMetadataManager()

    def natural_key(self):
        return [self.namespace]

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['namespace', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    url = models.URLField(null=True, blank=True, verify_exists=True)

    def __unicode__(self):
        return "{0} ({1})".format(self.name, self.url)

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
        return "{0} ({1})".format(self.user.get_full_name(), self.user.username)

    class Meta:
        abstract = True


class Experimenter(CommonsUser):
    approved = models.BooleanField(default=False)
    class Meta:
        ordering = ['user']

class GameConfiguration(models.Model):
    game = models.ForeignKey(GameMetadata)
    creator = models.ForeignKey(Experimenter)
    name = models.CharField(max_length=255)
    maximum_number_of_participants = models.PositiveIntegerField()
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True)

    def __unicode__(self):
        return "{name} (GameConfiguration) for {game} created by {creator} on {date_created}".format(name=self.name, game=self.game, creator=self.creator, date_created=self.date_created)

    class Meta:
        ordering = ['game', 'creator', 'date_created']


class GameInstanceManager(models.Manager):
    def get_all_active(self):
        return self.filter(status='ACTIVE')


# an actual instance of a game; represents a concrete
# parameterization of this game.
class GameInstance(models.Model):
    GAME_STATUS_CHOICES = (
                           ('INACTIVE', 'Not active'),
                           ('ACTIVE', 'Active'),
                           ('COMPLETED', 'Completed'),
                           )
    authentication_code = models.CharField(max_length=255)
    current_round_number = models.PositiveIntegerField()
    experimenter = models.ForeignKey(Experimenter)
    game_metadata = models.ForeignKey(GameMetadata)
    game_configuration = models.ForeignKey(GameConfiguration)
    status = models.CharField(max_length=32, choices=GAME_STATUS_CHOICES)
    date_created = models.DateTimeField(auto_now_add=True)
    start_date_time = models.DateTimeField(null=True, blank=True)
    # how long this experiment should run in a date format
    # 1w2d = 1 week 2 days = 9d
    duration = models.CharField(max_length=32)
    """
    how often the game server should tick.. 
    """
    tick_duration = models.CharField(max_length=32)
    end_date_time = models.DateTimeField(null=True, blank=True)
    """
    If true, signifies that this is an extended game that should execute over the course of a few days or even months, utilizes cron for scheduling 
    of events.
    
    If false, signifies that this is an experimenter-driven or short-term timer-driven game.
    """
    is_extended = models.BooleanField(default=False)

    objects = GameInstanceManager()

    @property
    def url(self, request):
        user = request.user
        if user.is_authenticated():
            return "/{0}/{1}".format("participant" if is_participant(user) else "experimenter", self.url_id)
        else:
            return self.namespace


    @property
    def participant_url(self):
        return "/participant/{0}".format(self.url_id)

    @property
    def management_url(self):
        return "/experimenter/{0}".format(self.url_id)

    @property
    def namespace(self):
        return self.game_metadata.namespace

    @property
    def url_id(self):
        return "{0}/{1}".format(self.game_metadata.namespace, self.id)

    def __unicode__(self):
        return "{game} created by {experimenter} on {date_created}: {status}".format(game=self.game_metadata, experimenter=self.experimenter, date_created=self.date_created, status=self.status)

    def ___eq___(self, other):
        return self.id == other.id

    def ___cmp___(self, other):
        return self.id.___cmp___(other.id)

    def ___hash___(self):
        return self.id.___hash___()

class RoundConfiguration(models.Model):
    game_configuration = models.ForeignKey(GameConfiguration)
    sequence_number = models.PositiveIntegerField()
    """
    How long should this round execute before advancing to the next?
    
    """
    duration = models.PositiveIntegerField()

    def __unicode__(self):
        return "Round # {0} for game {1} ".format(self.sequence_number, self.game_configuration)

#    class Meta:
#        db_table = 'vcweb_round_configuration'


class Parameter(models.Model):
    PARAMETER_TYPES = (
                    ('int', 'Integer'),
                    ('string', 'String'),
                    ('float', 'Float'),
                    ('boolean', (('True', True), ('False', False))),
                    ('enum', 'enum')
                    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)

    def __unicode__(self):
        return "{0} ({1})".format(self.name, self.type)

    class Meta:
        abstract = True
        ordering = ['name']

class ConfigurationParameter(Parameter):
    def __unicode__(self):
        return 'Configuration Parameter: ' + self.name

#    class Meta:
#        db_table = 'vcweb_configuration_parameter'


class DataParameter(Parameter):

    def ___eq___(self, other):
        return self.name == other.name

    def ___cmp___(self, other):
        return self.name.__cmp__(other.name)

    def ___hash___(self):
        return self.name.__hash__()


    def __unicode__(self):
        return "Name: {0} - Type: {1}".format(self.name, self.type)

#    class Meta:
#        db_table = 'vcweb_data_parameter'

# round parameters are 
class RoundParameter(models.Model):
    round_configuration = models.ForeignKey(RoundConfiguration, related_name='parameters')
    parameter = models.ForeignKey(ConfigurationParameter)
    parameter_value = models.CharField(max_length=255)

    def __unicode__(self):
        return "{0} -- Parameter: {1} Value: {2}".format(self.round_configuration, self.parameter, self.parameter_value)

class Group(models.Model):
    number = models.PositiveIntegerField()
    max_size = models.PositiveIntegerField()
    game_instance = models.ForeignKey(GameInstance)
    def __unicode__(self):
        return "Group #{0} in {1}".format(self.number, self.game_instance)

    class Meta:
        ordering = ['game_instance', 'number']


class GroupRoundData (models.Model):
    group = models.ForeignKey(Group)
    round = models.ForeignKey(RoundConfiguration)

    def __unicode__(self):
        return "Round Data for {0} in {1}".format(self.group, self.round)

#    class Meta:
#        db_table = 'vcweb_group_round_data'

class DataValue(models.Model):
    parameter = models.ForeignKey(DataParameter)
    parameter_value = models.CharField(max_length=255)
    # FIXME: change to DateTimeField
    time_recorded = models.DateTimeField(auto_now_add=True)
    game_instance = models.ForeignKey(GameInstance)

    @staticmethod
    def find(incoming_parameter, incoming_game_instance):
        DataValue.objects.filter(parameter=incoming_parameter, game_instance=incoming_game_instance)

    def __unicode__(self):
        return "Data value: parameter {0}, value {1}, time recorded {2}, game {3}".format(self.parameter, self.parameter_value, self.time_recorded, self.game_instance)

    class Meta:
        abstract = True

class GroupRoundDataValue(DataValue):
    group_round_data = models.ForeignKey(GroupRoundData)
    class Meta:
        ordering = [ 'parameter' ]

class Participant(CommonsUser):
    can_receive_invitations = models.BooleanField(default=False)
    group = models.ManyToManyField(Group, through='ParticipantGroup', related_name='groups')
#    objects = ParticipantManager()
    class Meta:
        ordering = ['user']


class ParticipantGroup(models.Model):
    participant_number = models.PositiveIntegerField()
    participant = models.ForeignKey(Participant)
    group = models.ForeignKey(Group)
    round_joined = models.ForeignKey(RoundConfiguration)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "{0}: {1} (in {2})".format(self.participant, self.participant_number, self.group)

    class Meta:
        ordering = ['participant_number', 'participant']

class ParticipantData(models.Model):
    participant = models.ForeignKey(Participant)
    round_configuration = models.ForeignKey(RoundConfiguration)

class ParticipantDataValue(DataValue):
    participant_data = models.ForeignKey(ParticipantData)

    class Meta:
        ordering = [ 'parameter' ]

class SessionTracker(models.Model):
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField()

class ExperimenterSession(SessionTracker):
    experimenter_id = models.ForeignKey(Experimenter)

class ParticipantSession(SessionTracker):
    participant_id = models.ForeignKey(Participant)

def is_experimenter(user):
    try:
        return user.experimenter
    except Experimenter.DoesNotExist:
        return None

def is_participant(user):
    try:
        return user.participant
    except Participant.DoesNotExist:
        return None


