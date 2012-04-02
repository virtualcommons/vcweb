# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExperimentMetadata'
        db.create_table('core_experimentmetadata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('namespace', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('short_name', self.gf('django.db.models.fields.SlugField')(max_length=32, unique=True, null=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('about_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('logo_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('default_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentConfiguration'], null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ExperimentMetadata'])

        # Adding model 'Institution'
        db.create_table('core_institution', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('core', ['Institution'])

        # Adding model 'Experimenter'
        db.create_table('core_experimenter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='experimenter', unique=True, to=orm['auth.User'])),
            ('failed_password_attempts', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Institution'], null=True, blank=True)),
            ('authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['Experimenter'])

        # Adding model 'ExperimentConfiguration'
        db.create_table('core_experimentconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_configuration_set', to=orm['core.ExperimentMetadata'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_configuration_set', to=orm['core.Experimenter'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('max_number_of_participants', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('date_created', self.gf('django.db.models.fields.DateField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_public', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('max_group_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
        ))
        db.send_create_signal('core', ['ExperimentConfiguration'])

        # Adding model 'Experiment'
        db.create_table('core_experiment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('authentication_code', self.gf('django.db.models.fields.CharField')(default='vcweb.auth.code', max_length=32)),
            ('current_round_sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('experimenter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentMetadata'])),
            ('experiment_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentConfiguration'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='INACTIVE', max_length=32)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('start_date_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('tick_duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('total_elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('current_round_start_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('current_round_elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('is_experimenter_driven', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('amqp_exchange_name', self.gf('django.db.models.fields.CharField')(default='vcweb.default.exchange', max_length=64)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=16, unique=True, null=True, blank=True)),
        ))
        db.send_create_signal('core', ['Experiment'])

        # Adding model 'RoundConfiguration'
        db.create_table('core_roundconfiguration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_configuration_set', to=orm['core.ExperimentConfiguration'])),
            ('sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('display_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('instructions', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('debriefing', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('round_type', self.gf('django.db.models.fields.CharField')(default='REGULAR', max_length=32)),
            ('template_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal('core', ['RoundConfiguration'])

        # Adding model 'QuizQuestion'
        db.create_table('core_quizquestion', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('input_type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('explanation', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='quiz_question_set', to=orm['core.RoundConfiguration'])),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='default_quiz_question_set', null=True, to=orm['core.Experiment'])),
        ))
        db.send_create_signal('core', ['QuizQuestion'])

        # Adding model 'Parameter'
        db.create_table('core_parameter', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scope', self.gf('django.db.models.fields.CharField')(default='round', max_length=32)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('default_value_string', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentMetadata'], null=True, blank=True)),
            ('enum_choices', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_required', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['Parameter'])

        # Adding unique constraint on 'Parameter', fields ['name', 'experiment_metadata', 'scope']
        db.create_unique('core_parameter', ['name', 'experiment_metadata_id', 'scope'])

        # Adding model 'RoundParameterValue'
        db.create_table('core_roundparametervalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_parameter_value_set', to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal('core', ['RoundParameterValue'])

        # Adding model 'Group'
        db.create_table('core_group', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experiment'])),
        ))
        db.send_create_signal('core', ['Group'])

        # Adding model 'RoundData'
        db.create_table('core_rounddata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_data_set', to=orm['core.Experiment'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_data_set', to=orm['core.RoundConfiguration'])),
            ('elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal('core', ['RoundData'])

        # Adding model 'GroupRoundDataValue'
        db.create_table('core_grouprounddatavalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='data_value_set', to=orm['core.Group'])),
            ('round_data', self.gf('django.db.models.fields.related.ForeignKey')(related_name='group_data_value_set', to=orm['core.RoundData'])),
        ))
        db.send_create_signal('core', ['GroupRoundDataValue'])

        # Adding model 'Participant'
        db.create_table('core_participant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='participant', unique=True, to=orm['auth.User'])),
            ('failed_password_attempts', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Institution'], null=True, blank=True)),
            ('authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('can_receive_invitations', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('core', ['Participant'])

        # Adding model 'ParticipantExperimentRelationship'
        db.create_table('core_participantexperimentrelationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_relationship_set', to=orm['core.Participant'])),
            ('participant_identifier', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('sequential_participant_identifier', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_relationship_set', to=orm['core.Experiment'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('last_completed_round_sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('current_location', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('additional_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ParticipantExperimentRelationship'])

        # Adding model 'ParticipantGroupRelationship'
        db.create_table('core_participantgrouprelationship', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_group_relationship_set', to=orm['core.Participant'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_group_relationship_set', to=orm['core.Group'])),
            ('round_joined', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('notifications_since', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
        ))
        db.send_create_signal('core', ['ParticipantGroupRelationship'])

        # Adding model 'ParticipantRoundDataValue'
        db.create_table('core_participantrounddatavalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('round_data', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_data_value_set', to=orm['core.RoundData'])),
            ('participant_group_relationship', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_data_value_set', to=orm['core.ParticipantGroupRelationship'])),
            ('submitted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('target_data_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target_data_value_set', null=True, to=orm['core.ParticipantRoundDataValue'])),
        ))
        db.send_create_signal('core', ['ParticipantRoundDataValue'])

        # Adding model 'ChatMessage'
        db.create_table('core_chatmessage', (
            ('participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
            ('target_participant', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target_participant_chat_message_set', null=True, to=orm['core.ParticipantGroupRelationship'])),
        ))
        db.send_create_signal('core', ['ChatMessage'])

        # Adding model 'Comment'
        db.create_table('core_comment', (
            ('participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('core', ['Comment'])

        # Adding model 'Like'
        db.create_table('core_like', (
            ('participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
        ))
        db.send_create_signal('core', ['Like'])

        # Adding model 'ActivityLog'
        db.create_table('core_activitylog', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('log_message', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('core', ['ActivityLog'])

        # Adding model 'GroupActivityLog'
        db.create_table('core_groupactivitylog', (
            ('activitylog_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ActivityLog'], unique=True, primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log_set', to=orm['core.Group'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal('core', ['GroupActivityLog'])

        # Adding model 'ExperimentActivityLog'
        db.create_table('core_experimentactivitylog', (
            ('activitylog_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ActivityLog'], unique=True, primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log_set', to=orm['core.Experiment'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal('core', ['ExperimentActivityLog'])

    def backwards(self, orm):
        # Removing unique constraint on 'Parameter', fields ['name', 'experiment_metadata', 'scope']
        db.delete_unique('core_parameter', ['name', 'experiment_metadata_id', 'scope'])

        # Deleting model 'ExperimentMetadata'
        db.delete_table('core_experimentmetadata')

        # Deleting model 'Institution'
        db.delete_table('core_institution')

        # Deleting model 'Experimenter'
        db.delete_table('core_experimenter')

        # Deleting model 'ExperimentConfiguration'
        db.delete_table('core_experimentconfiguration')

        # Deleting model 'Experiment'
        db.delete_table('core_experiment')

        # Deleting model 'RoundConfiguration'
        db.delete_table('core_roundconfiguration')

        # Deleting model 'QuizQuestion'
        db.delete_table('core_quizquestion')

        # Deleting model 'Parameter'
        db.delete_table('core_parameter')

        # Deleting model 'RoundParameterValue'
        db.delete_table('core_roundparametervalue')

        # Deleting model 'Group'
        db.delete_table('core_group')

        # Deleting model 'RoundData'
        db.delete_table('core_rounddata')

        # Deleting model 'GroupRoundDataValue'
        db.delete_table('core_grouprounddatavalue')

        # Deleting model 'Participant'
        db.delete_table('core_participant')

        # Deleting model 'ParticipantExperimentRelationship'
        db.delete_table('core_participantexperimentrelationship')

        # Deleting model 'ParticipantGroupRelationship'
        db.delete_table('core_participantgrouprelationship')

        # Deleting model 'ParticipantRoundDataValue'
        db.delete_table('core_participantrounddatavalue')

        # Deleting model 'ChatMessage'
        db.delete_table('core_chatmessage')

        # Deleting model 'Comment'
        db.delete_table('core_comment')

        # Deleting model 'Like'
        db.delete_table('core_like')

        # Deleting model 'ActivityLog'
        db.delete_table('core_activitylog')

        # Deleting model 'GroupActivityLog'
        db.delete_table('core_groupactivitylog')

        # Deleting model 'ExperimentActivityLog'
        db.delete_table('core_experimentactivitylog')

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'core.activitylog': {
            'Meta': {'object_name': 'ActivityLog'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_message': ('django.db.models.fields.TextField', [], {})
        },
        'core.chatmessage': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'ChatMessage', '_ormbases': ['core.ParticipantRoundDataValue']},
            'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'}),
            'target_participant': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_participant_chat_message_set'", 'null': 'True', 'to': "orm['core.ParticipantGroupRelationship']"})
        },
        'core.comment': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'Comment', '_ormbases': ['core.ParticipantRoundDataValue']},
            'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        'core.experiment': {
            'Meta': {'ordering': "['date_created', 'status']", 'object_name': 'Experiment'},
            'amqp_exchange_name': ('django.db.models.fields.CharField', [], {'default': "'vcweb.default.exchange'", 'max_length': '64'}),
            'authentication_code': ('django.db.models.fields.CharField', [], {'default': "'vcweb.auth.code'", 'max_length': '32'}),
            'current_round_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'current_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'current_round_start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']"}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '16', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'start_date_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INACTIVE'", 'max_length': '32'}),
            'tick_duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'total_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'core.experimentactivitylog': {
            'Meta': {'object_name': 'ExperimentActivityLog', '_ormbases': ['core.ActivityLog']},
            'activitylog_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ActivityLog']", 'unique': 'True', 'primary_key': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log_set'", 'to': "orm['core.Experiment']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.experimentconfiguration': {
            'Meta': {'ordering': "['experiment_metadata', 'creator', 'date_created']", 'object_name': 'ExperimentConfiguration'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': "orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': "orm['core.ExperimentMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.experimenter': {
            'Meta': {'ordering': "['user']", 'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'experimenter'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'core.experimentmetadata': {
            'Meta': {'ordering': "['namespace', 'date_created']", 'object_name': 'ExperimentMetadata'},
            'about_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'logo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'namespace': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'short_name': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.groupactivitylog': {
            'Meta': {'object_name': 'GroupActivityLog', '_ormbases': ['core.ActivityLog']},
            'activitylog_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ActivityLog']", 'unique': 'True', 'primary_key': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log_set'", 'to': "orm['core.Group']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.grouprounddatavalue': {
            'Meta': {'ordering': "['round_data', 'group', 'parameter']", 'object_name': 'GroupRoundDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data_value_set'", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_data_value_set'", 'to': "orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.institution': {
            'Meta': {'object_name': 'Institution'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'core.like': {
            'Meta': {'ordering': "['round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'Like', '_ormbases': ['core.ParticipantRoundDataValue']},
            'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        'core.parameter': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'experiment_metadata', 'scope'),)", 'object_name': 'Parameter'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'default_value_string': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'enum_choices': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentMetadata']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'scope': ('django.db.models.fields.CharField', [], {'default': "'round'", 'max_length': '32'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'core.participant': {
            'Meta': {'ordering': "['user']", 'object_name': 'Participant'},
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'can_receive_invitations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'experiments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': "orm['core.ParticipantExperimentRelationship']", 'to': "orm['core.Experiment']"}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': "orm['core.ParticipantGroupRelationship']", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'participant'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'core.participantexperimentrelationship': {
            'Meta': {'object_name': 'ParticipantExperimentRelationship'},
            'additional_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'current_location': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_relationship_set'", 'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_completed_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_relationship_set'", 'to': "orm['core.Participant']"}),
            'participant_identifier': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'sequential_participant_identifier': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'core.participantgrouprelationship': {
            'Meta': {'ordering': "['group', 'participant_number']", 'object_name': 'ParticipantGroupRelationship'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notifications_since': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Participant']"}),
            'participant_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'round_joined': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.participantrounddatavalue': {
            'Meta': {'ordering': "['round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'ParticipantRoundDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'participant_group_relationship': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': "orm['core.ParticipantGroupRelationship']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': "orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'submitted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_data_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_data_value_set'", 'null': 'True', 'to': "orm['core.ParticipantRoundDataValue']"})
        },
        'core.quizquestion': {
            'Meta': {'object_name': 'QuizQuestion'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'default_quiz_question_set'", 'null': 'True', 'to': "orm['core.Experiment']"}),
            'explanation': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'quiz_question_set'", 'to': "orm['core.RoundConfiguration']"})
        },
        'core.roundconfiguration': {
            'Meta': {'ordering': "['experiment_configuration', 'sequence_number', 'date_created']", 'object_name': 'RoundConfiguration'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'debriefing': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_configuration_set'", 'to': "orm['core.ExperimentConfiguration']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'round_type': ('django.db.models.fields.CharField', [], {'default': "'REGULAR'", 'max_length': '32'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'template_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'core.rounddata': {
            'Meta': {'ordering': "['round_configuration']", 'object_name': 'RoundData'},
            'elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': "orm['core.Experiment']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': "orm['core.RoundConfiguration']"})
        },
        'core.roundparametervalue': {
            'Meta': {'object_name': 'RoundParameterValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_parameter_value_set'", 'to': "orm['core.RoundConfiguration']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['core']