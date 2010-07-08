# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'GameMetadata'
        db.create_table('core_gamemetadata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateField')(auto_now=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('default_game_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameConfiguration'], null=True, blank=True)),
        ))
        db.send_create_signal('core', ['GameMetadata'])

        # Adding model 'Experimenter'
        db.create_table('core_experimenter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('last_name', self.gf('django.db.models.fields.TextField')()),
            ('first_name', self.gf('django.db.models.fields.TextField')()),
            ('institution', self.gf('django.db.models.fields.TextField')()),
            ('password', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('approved', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('last_login_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('failed_password_attempts', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('core', ['Experimenter'])

        # Adding model 'GameConfiguration'
        db.create_table('core_gameconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameMetadata'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('maximum_number_of_participants', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('date_created', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateField')(auto_now=True, blank=True)),
            ('is_public', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
        ))
        db.send_create_signal('core', ['GameConfiguration'])

        # Adding model 'RoundConfiguration'
        db.create_table('core_roundconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('game_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameConfiguration'])),
            ('sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('core', ['RoundConfiguration'])

        # Adding model 'ConfigurationParameter'
        db.create_table('core_configurationparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length='32')),
        ))
        db.send_create_signal('core', ['ConfigurationParameter'])

        # Adding model 'DataParameter'
        db.create_table('core_dataparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length='32')),
        ))
        db.send_create_signal('core', ['DataParameter'])

        # Adding model 'RoundParameter'
        db.create_table('core_roundparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ConfigurationParameter'])),
            ('parameter_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('core', ['RoundParameter'])

        # Adding model 'GameInstance'
        db.create_table('core_gameinstance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('authentication_code', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('current_round_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('experimenter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('game_metadata', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameMetadata'])),
            ('game_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameConfiguration'])),
        ))
        db.send_create_signal('core', ['GameInstance'])

        # Adding model 'Group'
        db.create_table('core_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('game_instance', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GameInstance'])),
        ))
        db.send_create_signal('core', ['Group'])

        # Adding model 'GroupRoundData'
        db.create_table('core_grouprounddata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
            ('round', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal('core', ['GroupRoundData'])

        # Adding model 'GroupRoundDataParameter'
        db.create_table('core_grouprounddataparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('group_round_data', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GroupRoundData'])),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.DataParameter'])),
            ('parameter_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('core', ['GroupRoundDataParameter'])

        # Adding model 'Participant'
        db.create_table('core_participant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=75)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
        ))
        db.send_create_signal('core', ['Participant'])

        # Adding model 'ParticipantData'
        db.create_table('core_participantdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Participant'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal('core', ['ParticipantData'])

        # Adding model 'ParticipantDataParameter'
        db.create_table('core_participantdataparameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant_data', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ParticipantData'])),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.DataParameter'])),
            ('parameter_value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('core', ['ParticipantDataParameter'])


    def backwards(self, orm):
        
        # Deleting model 'GameMetadata'
        db.delete_table('core_gamemetadata')

        # Deleting model 'Experimenter'
        db.delete_table('core_experimenter')

        # Deleting model 'GameConfiguration'
        db.delete_table('core_gameconfiguration')

        # Deleting model 'RoundConfiguration'
        db.delete_table('core_roundconfiguration')

        # Deleting model 'ConfigurationParameter'
        db.delete_table('core_configurationparameter')

        # Deleting model 'DataParameter'
        db.delete_table('core_dataparameter')

        # Deleting model 'RoundParameter'
        db.delete_table('core_roundparameter')

        # Deleting model 'GameInstance'
        db.delete_table('core_gameinstance')

        # Deleting model 'Group'
        db.delete_table('core_group')

        # Deleting model 'GroupRoundData'
        db.delete_table('core_grouprounddata')

        # Deleting model 'GroupRoundDataParameter'
        db.delete_table('core_grouprounddataparameter')

        # Deleting model 'Participant'
        db.delete_table('core_participant')

        # Deleting model 'ParticipantData'
        db.delete_table('core_participantdata')

        # Deleting model 'ParticipantDataParameter'
        db.delete_table('core_participantdataparameter')


    models = {
        'core.configurationparameter': {
            'Meta': {'object_name': 'ConfigurationParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': "'32'"})
        },
        'core.dataparameter': {
            'Meta': {'object_name': 'DataParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': "'32'"})
        },
        'core.experimenter': {
            'Meta': {'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'first_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.TextField', [], {}),
            'last_login_date': ('django.db.models.fields.DateTimeField', [], {}),
            'last_name': ('django.db.models.fields.TextField', [], {}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.gameconfiguration': {
            'Meta': {'object_name': 'GameConfiguration'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'game': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'blank': 'True'}),
            'maximum_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.gameinstance': {
            'Meta': {'object_name': 'GameInstance'},
            'authentication_code': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'current_round_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'game_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameConfiguration']"}),
            'game_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'core.gamemetadata': {
            'Meta': {'object_name': 'GameMetadata'},
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_game_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameConfiguration']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'core.group': {
            'Meta': {'object_name': 'Group'},
            'game_instance': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameInstance']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.grouprounddata': {
            'Meta': {'object_name': 'GroupRoundData'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'round': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.grouprounddataparameter': {
            'Meta': {'object_name': 'GroupRoundDataParameter'},
            'group_round_data': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GroupRoundData']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.DataParameter']"}),
            'parameter_value': ('django.db.models.fields.TextField', [], {})
        },
        'core.participant': {
            'Meta': {'object_name': 'Participant'},
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '75'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.participantdata': {
            'Meta': {'object_name': 'ParticipantData'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Participant']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.participantdataparameter': {
            'Meta': {'object_name': 'ParticipantDataParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.DataParameter']"}),
            'parameter_value': ('django.db.models.fields.TextField', [], {}),
            'participant_data': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ParticipantData']"})
        },
        'core.roundconfiguration': {
            'Meta': {'object_name': 'RoundConfiguration'},
            'game_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.GameConfiguration']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.roundparameter': {
            'Meta': {'object_name': 'RoundParameter'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ConfigurationParameter']"}),
            'parameter_value': ('django.db.models.fields.TextField', [], {}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        }
    }

    complete_apps = ['core']
