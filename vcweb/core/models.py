from django.db import models

# FIXME: split this into multiple modules or have one monolithic models file?  Seems
# like the standard is to have a single models.py per app

# Create your models here.
class GameMetadata(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    url = models.URLField()
    default_game_configuration = models.ForeignKey('GameConfiguration', null=True, blank=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        ordering = ['name', 'date_created']

class Institution(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    url = models.URLField(null=True)

class Experimenter(models.Model):
    email = models.EmailField()
    last_name = models.CharField(max_length=64)
    first_name = models.CharField(max_length=64)
    institution = models.ForeignKey(Institution)
    password = models.CharField(max_length=255)
    approved = models.BooleanField()
    last_login_date = models.DateTimeField()
    failed_password_attempts = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['last_name', 'first_name', 'email']

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
    status = models.CharField(max_length=32, choices = GAME_STATUS_CHOICES)
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
    
#    class Meta:
#        db_table = 'vcweb_round_parameter'
    


    
#    class Meta:
#        db_table = 'vcweb_game_instance'
    
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
    time_recorded = models.TimeField(auto_now_add = True)
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


class Participant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    number = models.PositiveIntegerField()
    group = models.ForeignKey(Group)
    date_created = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ['number']
    
class ParticipantData(models.Model):
    participant = models.ForeignKey(Participant)
    round_configuration = models.ForeignKey(RoundConfiguration)
    
class ParticipantDataValue(DataValue):
    participant_data = models.ForeignKey(ParticipantData)
    
    class Meta:
        ordering = [ 'parameter' ]
    


