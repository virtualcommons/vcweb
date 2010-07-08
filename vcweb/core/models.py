from django.db import models

# may split this into multiple modules?

# Create your models here.
class GameMetadata(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    url = models.URLField()
    default_game_configuration = models.ForeignKey('GameConfiguration')
    
    def __unicode__(self):
        return self.name
    
#    class Meta:
#        db_table = 'vcweb_game_metadata'

class Experimenter(models.Model):
    email = models.EmailField()
    password = models.CharField(max_length=255)
    approved = models.BooleanField()
    last_login_date = models.DateTimeField()
    failed_password_attempts = models.PositiveIntegerField()
    
#    class Meta:
#        db_table = 'vcweb_experimenter'

class GameConfiguration(models.Model):    
    game = models.ForeignKey(GameMetadata)
    creator = models.ForeignKey(Experimenter)
    name = models.CharField(max_length=255)
    maximum_number_of_participants = models.PositiveIntegerField()
    date_created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)
    is_public = models.BooleanField(default=True)

    
#    class Meta:
#        db_table = 'vcweb_game_configuration'
    
    
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
    type = models.CharField(max_length='32', choices=PARAMETER_TYPES)
    
    class Meta:
        abstract = True
        
class ConfigurationParameter(Parameter):
    def __unicode__(self):
        return 'Configuration Parameter: ' + self.name
    
#    class Meta:
#        db_table = 'vcweb_configuration_parameter'
     
     
class DataParameter(Parameter):
    def __unicode__(self):
        return 'Data Parameter - [name: ' + self.name + '] [type: ' + self.type + ']'
    
#    class Meta:
#        db_table = 'vcweb_data_parameter'
    
# round parameters are 
class RoundParameter(models.Model):
    round_configuration = models.ForeignKey(RoundConfiguration)
    parameter = models.ForeignKey(ConfigurationParameter)
    parameter_value = models.TextField()
    
#    class Meta:
#        db_table = 'vcweb_round_parameter'
    

# an actual instance of a game; represents a concrete
# parameterization of this game.
class GameInstance(models.Model):
    authentication_code = models.CharField(max_length=255)
    current_round_number = models.PositiveIntegerField()
    experimenter = models.ForeignKey(Experimenter)
    game = models.ForeignKey(GameMetadata)
    game_configuration = models.ForeignKey(GameConfiguration)
    
#    class Meta:
#        db_table = 'vcweb_game_instance'
    
class Group(models.Model):
    number = models.PositiveIntegerField()
    max_size = models.PositiveIntegerField()
    def __unicode__(self):
        return 'Group ' + self.number
    
    
class GroupRoundData (models.Model):
    group = models.ForeignKey(Group)
    round = models.ForeignKey(RoundConfiguration)
    
#    class Meta:
#        db_table = 'vcweb_group_round_data'


class GroupRoundDataParameter(models.Model):
    group_round_data = models.ForeignKey(GroupRoundData)
    parameter = models.ForeignKey(DataParameter)
    parameter_value = models.TextField()
    
#    class Meta:
#        ordering = [ 'parameter' ]
    

class Participant(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    number = models.PositiveIntegerField()
    group = models.ForeignKey(Group)
    
class ParticipantData(models.Model):
    participant = models.ForeignKey(Participant)
    round_configuration = models.ForeignKey(RoundConfiguration)
    
class ParticipantDataParameter(models.Model):
    participant_data = models.ForeignKey(ParticipantData)
    parameter = models.ForeignKey(DataParameter)
    parameter_value = models.TextField()
    
    
     



    
    

