from django.contrib.auth.models import User, UserManager
from django.core.validators import RegexValidator
from django.db import models

import logging

logger = logging.getLogger('vcweb.core.models')
# FIXME: split this into multiple modules or have one monolithic models file?  Seems
# like the standard is to have a single models.py per app

# Create your models here.
class GameMetadata(models.Model):
    title = models.CharField(max_length=255)
    # the URL namespace that this game will occupy
    namespace = models.CharField(max_length=255, unique=True, validators=[RegexValidator(regex=r'^\w+$'), ])
    description = models.TextField(null=True)
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    about_url = models.URLField(null=True, verify_exists=True)
    logo_url = models.URLField(null=True, verify_exists=True)
    default_game_configuration = models.ForeignKey('GameConfiguration', null=True)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['namespace', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    url = models.URLField(null=True, verify_exists=True)

class CommonsUser(models.Model):
    # for docs on related_name see http://docs.djangoproject.com/en/dev/topics/db/models/#be-careful-with-related-name
    user = models.OneToOneField(User, related_name='%(class)s', verbose_name=u'Django User', unique=True)
    failed_password_attempts = models.PositiveIntegerField(default=0)

    def is_authenticated(self):
        return self.user.is_authenticated()

    @property
    def backend(self):
        return self.user.backend

    @property
    def get_and_delete_messages(self):
        return self.user.get_and_delete_messages()

    def __unicode__(self):
        return self.user.__unicode__()

    class Meta:
        abstract = True


class Experimenter(CommonsUser):
    institution = models.ForeignKey(Institution)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['user']


class GameConfiguration(models.Model):
    game = models.ForeignKey(GameMetadata)
    creator = models.ForeignKey(Experimenter)
    name = models.CharField(max_length=255)
    maximum_number_of_participants = models.PositiveIntegerField()
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['game', 'creator', 'date_created']

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
    time_started = models.TimeField(null=True)
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)

    def ___eq___(self, other):
        return self.id == other.id

    def ___cmp___(self, other):
        return self.id.___cmp___(other.id)

    def ___hash___(self):
        return self.id.___hash___()

class RoundConfiguration(models.Model):
    game_configuration = models.ForeignKey(GameConfiguration)
    sequence_number = models.PositiveIntegerField(blank=False)

#    class Meta:
#        db_table = 'vcweb_round_configuration'


class Parameter(models.Model):
    PARAMETER_TYPES = (
                    ('int', 'Integer'),
                    ('string', 'String'),
                    ('float', 'Float'),
                    ('boolean', (('True', True), ('False', False))),
                    )
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=PARAMETER_TYPES)

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
        return 'Data Parameter - [name: ' + self.name + '] [type: ' + self.type + ']'

#    class Meta:
#        db_table = 'vcweb_data_parameter'

# round parameters are 
class RoundParameter(models.Model):
    round_configuration = models.ForeignKey(RoundConfiguration)
    parameter = models.ForeignKey(ConfigurationParameter)
    parameter_value = models.CharField(max_length=255)

class Group(models.Model):
    number = models.PositiveIntegerField()
    max_size = models.PositiveIntegerField()
    game_instance = models.ForeignKey(GameInstance)
    def __unicode__(self):
        return 'Group ' + self.number

    class Meta:
        ordering = ['game_instance', 'number']


class GroupRoundData (models.Model):
    group = models.ForeignKey(Group)
    round = models.ForeignKey(RoundConfiguration)

#    class Meta:
#        db_table = 'vcweb_group_round_data'

class DataValue(models.Model):
    parameter = models.ForeignKey(DataParameter)
    parameter_value = models.CharField(max_length=255)
    time_recorded = models.TimeField(auto_now_add=True)
    game_instance = models.ForeignKey(GameInstance)

    @staticmethod
    def find(incoming_parameter, incoming_game_instance):
        DataValue.objects.filter(parameter=incoming_parameter, game_instance=incoming_game_instance)


    class Meta:
        abstract = True

class GroupRoundDataValue(DataValue):
    group_round_data = models.ForeignKey(GroupRoundData)
    class Meta:
        ordering = [ 'parameter' ]

class Participant(CommonsUser):
    number = models.PositiveIntegerField()
    group = models.ForeignKey(Group)
    class Meta:
        ordering = ['number']

class ParticipantData(models.Model):
    participant = models.ForeignKey(Participant)
    round_configuration = models.ForeignKey(RoundConfiguration)

class ParticipantDataValue(DataValue):
    participant_data = models.ForeignKey(ParticipantData)

    class Meta:
        ordering = [ 'parameter' ]

class Session(models.Model):
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField()

class ExperimenterSession(Session):
    experimenter_id = models.ForeignKey(Experimenter)

class ParticipantSession(Session):
    participant_id = models.ForeignKey(Participant)




