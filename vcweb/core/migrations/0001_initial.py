# -*- coding: utf-8 -*-
import datetime

from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ExperimentMetadata'
        db.create_table(u'core_experimentmetadata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('namespace', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('short_name', self.gf('django.db.models.fields.SlugField')(max_length=32, unique=True, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('about_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('logo_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('default_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentConfiguration'], null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ExperimentMetadata'])

        # Adding model 'Institution'
        db.create_table(u'core_institution', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'core', ['Institution'])

        # Adding model 'Experimenter'
        db.create_table(u'core_experimenter', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='experimenter', unique=True, to=orm['auth.User'])),
            ('failed_password_attempts', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Institution'], null=True, blank=True)),
            ('authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Experimenter'])

        # Adding model 'ExperimenterRequest'
        db.create_table(u'core_experimenterrequest', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('approved', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['ExperimenterRequest'])

        # Adding model 'ExperimentConfiguration'
        db.create_table(u'core_experimentconfiguration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_configuration_set', to=orm['core.ExperimentMetadata'])),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_configuration_set', to=orm['core.Experimenter'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('max_number_of_participants', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('invitation_subject', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('invitation_text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('max_group_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
            ('exchange_rate', self.gf('django.db.models.fields.DecimalField')(default=0.2, null=True, max_digits=6, decimal_places=2, blank=True)),
            ('treatment_id', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('is_experimenter_driven', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'core', ['ExperimentConfiguration'])

        # Adding model 'Experiment'
        db.create_table(u'core_experiment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('authentication_code', self.gf('django.db.models.fields.CharField')(default='vcweb.auth.code', max_length=32)),
            ('current_round_sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('current_repeated_round_sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('experimenter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentMetadata'])),
            ('experiment_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentConfiguration'])),
            ('status', self.gf('django.db.models.fields.CharField')(default='INACTIVE', max_length=32)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('start_date_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('tick_duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('total_elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('current_round_start_time', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('current_round_elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('amqp_exchange_name', self.gf('django.db.models.fields.CharField')(default='vcweb.default.exchange', max_length=64)),
        ))
        db.send_create_signal(u'core', ['Experiment'])

        # Adding model 'RoundConfiguration'
        db.create_table(u'core_roundconfiguration', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_configuration_set', to=orm['core.ExperimentConfiguration'])),
            ('sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('display_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('duration', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('instructions', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('debriefing', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('round_type', self.gf('django.db.models.fields.CharField')(default='REGULAR', max_length=32)),
            ('template_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('survey_url', self.gf('django.db.models.fields.URLField')(max_length=200, null=True, blank=True)),
            ('chat_enabled', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('create_group_clusters', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('group_cluster_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=2)),
            ('randomize_groups', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('preserve_existing_groups', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('repeat', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'core', ['RoundConfiguration'])

        # Adding model 'QuizQuestion'
        db.create_table(u'core_quizquestion', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('input_type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('explanation', self.gf('django.db.models.fields.CharField')(max_length=512)),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='quiz_question_set', to=orm['core.RoundConfiguration'])),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='default_quiz_question_set', null=True, to=orm['core.Experiment'])),
        ))
        db.send_create_signal(u'core', ['QuizQuestion'])

        # Adding model 'Parameter'
        db.create_table(u'core_parameter', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('scope', self.gf('django.db.models.fields.CharField')(default='round', max_length=32)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=512, null=True, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('class_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('default_value_string', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experimenter'])),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentMetadata'], null=True, blank=True)),
            ('enum_choices', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('is_required', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'core', ['Parameter'])

        # Adding unique constraint on 'Parameter', fields ['name', 'experiment_metadata', 'scope']
        db.create_unique(u'core_parameter', ['name', 'experiment_metadata_id', 'scope'])

        # Adding model 'ExperimentParameterValue'
        db.create_table(u'core_experimentparametervalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('experiment_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_parameter_value_set', to=orm['core.ExperimentConfiguration'])),
        ))
        db.send_create_signal(u'core', ['ExperimentParameterValue'])

        # Adding model 'RoundParameterValue'
        db.create_table(u'core_roundparametervalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_parameter_value_set', to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal(u'core', ['RoundParameterValue'])

        # Adding model 'Group'
        db.create_table(u'core_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('max_size', self.gf('django.db.models.fields.PositiveIntegerField')(default=5)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experiment'])),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Group'])

        # Adding model 'GroupCluster'
        db.create_table(u'core_groupcluster', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Experiment'])),
        ))
        db.send_create_signal(u'core', ['GroupCluster'])

        # Adding model 'GroupRelationship'
        db.create_table(u'core_grouprelationship', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('cluster', self.gf('django.db.models.fields.related.ForeignKey')(related_name='group_set', to=orm['core.GroupCluster'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Group'])),
        ))
        db.send_create_signal(u'core', ['GroupRelationship'])

        # Adding model 'RoundData'
        db.create_table(u'core_rounddata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_data_set', to=orm['core.Experiment'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(related_name='round_data_set', to=orm['core.RoundConfiguration'])),
            ('elapsed_time', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('experimenter_notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['RoundData'])

        # Adding unique constraint on 'RoundData', fields ['round_configuration', 'experiment']
        db.create_unique(u'core_rounddata', ['round_configuration_id', 'experiment_id'])

        # Adding model 'GroupClusterDataValue'
        db.create_table(u'core_groupclusterdatavalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('group_cluster', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.GroupCluster'])),
            ('round_data', self.gf('django.db.models.fields.related.ForeignKey')(related_name='group_cluster_data_value_set', to=orm['core.RoundData'])),
        ))
        db.send_create_signal(u'core', ['GroupClusterDataValue'])

        # Adding model 'GroupRoundDataValue'
        db.create_table(u'core_grouprounddatavalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='data_value_set', to=orm['core.Group'])),
            ('round_data', self.gf('django.db.models.fields.related.ForeignKey')(related_name='group_data_value_set', to=orm['core.RoundData'])),
        ))
        db.send_create_signal(u'core', ['GroupRoundDataValue'])

        # Adding model 'Address'
        db.create_table(u'core_address', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('street1', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('street2', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('city', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('zipcode', self.gf('django.db.models.fields.CharField')(max_length=8, blank=True)),
        ))
        db.send_create_signal(u'core', ['Address'])

        # Adding model 'Participant'
        db.create_table(u'core_participant', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='participant', unique=True, to=orm['auth.User'])),
            ('failed_password_attempts', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('institution', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Institution'], null=True, blank=True)),
            ('authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('can_receive_invitations', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('gender', self.gf('django.db.models.fields.CharField')(max_length=1, blank=True)),
            ('birthdate', self.gf('django.db.models.fields.DateField')(null=True, blank=True)),
            ('address', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Address'], null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['Participant'])

        # Adding model 'ParticipantExperimentRelationship'
        db.create_table(u'core_participantexperimentrelationship', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_relationship_set', to=orm['core.Participant'])),
            ('participant_identifier', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('sequential_participant_identifier', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_relationship_set', to=orm['core.Experiment'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('created_by', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('last_completed_round_sequence_number', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('current_location', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('additional_data', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ParticipantExperimentRelationship'])

        # Adding model 'ParticipantGroupRelationship'
        db.create_table(u'core_participantgrouprelationship', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant_number', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_group_relationship_set', to=orm['core.Participant'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_group_relationship_set', to=orm['core.Group'])),
            ('round_joined', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('first_visit', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('notifications_since', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ParticipantGroupRelationship'])

        # Adding model 'ParticipantRoundDataValue'
        db.create_table(u'core_participantrounddatavalue', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parameter', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Parameter'])),
            ('string_value', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('boolean_value', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now, db_index=True)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('is_active', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('round_data', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_data_value_set', to=orm['core.RoundData'])),
            ('participant_group_relationship', self.gf('django.db.models.fields.related.ForeignKey')(related_name='participant_data_value_set', to=orm['core.ParticipantGroupRelationship'])),
            ('submitted', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('target_data_value', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target_data_value_set', null=True, to=orm['core.ParticipantRoundDataValue'])),
        ))
        db.send_create_signal(u'core', ['ParticipantRoundDataValue'])

        # Adding model 'ChatMessage'
        db.create_table(u'core_chatmessage', (
            (u'participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
            ('target_participant', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='target_participant_chat_message_set', null=True, to=orm['core.ParticipantGroupRelationship'])),
        ))
        db.send_create_signal(u'core', ['ChatMessage'])

        # Adding model 'Comment'
        db.create_table(u'core_comment', (
            (u'participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'core', ['Comment'])

        # Adding model 'Like'
        db.create_table(u'core_like', (
            (u'participantrounddatavalue_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ParticipantRoundDataValue'], unique=True, primary_key=True)),
        ))
        db.send_create_signal(u'core', ['Like'])

        # Adding model 'ActivityLog'
        db.create_table(u'core_activitylog', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('log_message', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
        ))
        db.send_create_signal(u'core', ['ActivityLog'])

        # Adding model 'GroupActivityLog'
        db.create_table(u'core_groupactivitylog', (
            (u'activitylog_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ActivityLog'], unique=True, primary_key=True)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log_set', to=orm['core.Group'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal(u'core', ['GroupActivityLog'])

        # Adding model 'ExperimentActivityLog'
        db.create_table(u'core_experimentactivitylog', (
            (u'activitylog_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['core.ActivityLog'], unique=True, primary_key=True)),
            ('experiment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='activity_log_set', to=orm['core.Experiment'])),
            ('round_configuration', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.RoundConfiguration'])),
        ))
        db.send_create_signal(u'core', ['ExperimentActivityLog'])

        # Adding model 'ExperimentSession'
        db.create_table(u'core_experimentsession', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('experiment_metadata', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_session_set', to=orm['core.ExperimentMetadata'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('scheduled_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('scheduled_end_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('capacity', self.gf('django.db.models.fields.PositiveIntegerField')(default=20)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(related_name='experiment_session_set', to=orm['auth.User'])),
            ('invitation_text', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ExperimentSession'])

        # Adding model 'Invitation'
        db.create_table(u'core_invitation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.Participant'])),
            ('experiment_session', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['core.ExperimentSession'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('sender', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'core', ['Invitation'])

        # Adding model 'ParticipantSignup'
        db.create_table(u'core_participantsignup', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='signup_set', to=orm['core.Participant'])),
            ('invitation', self.gf('django.db.models.fields.related.ForeignKey')(related_name='signup_set', to=orm['core.Invitation'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('attendance', self.gf('django.db.models.fields.PositiveIntegerField')(max_length=1, null=True, blank=True)),
        ))
        db.send_create_signal(u'core', ['ParticipantSignup'])

        # Adding model 'SpoolParticipantStatistics'
        db.create_table(u'core_spoolparticipantstatistics', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant', self.gf('django.db.models.fields.related.ForeignKey')(related_name='spool_statistics_set', to=orm['core.Participant'])),
            ('absences', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('discharges', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('participations', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('invitations', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
        ))
        db.send_create_signal(u'core', ['SpoolParticipantStatistics'])


    def backwards(self, orm):
        # Removing unique constraint on 'RoundData', fields ['round_configuration', 'experiment']
        db.delete_unique(u'core_rounddata', ['round_configuration_id', 'experiment_id'])

        # Removing unique constraint on 'Parameter', fields ['name', 'experiment_metadata', 'scope']
        db.delete_unique(u'core_parameter', ['name', 'experiment_metadata_id', 'scope'])

        # Deleting model 'ExperimentMetadata'
        db.delete_table(u'core_experimentmetadata')

        # Deleting model 'Institution'
        db.delete_table(u'core_institution')

        # Deleting model 'Experimenter'
        db.delete_table(u'core_experimenter')

        # Deleting model 'ExperimenterRequest'
        db.delete_table(u'core_experimenterrequest')

        # Deleting model 'ExperimentConfiguration'
        db.delete_table(u'core_experimentconfiguration')

        # Deleting model 'Experiment'
        db.delete_table(u'core_experiment')

        # Deleting model 'RoundConfiguration'
        db.delete_table(u'core_roundconfiguration')

        # Deleting model 'QuizQuestion'
        db.delete_table(u'core_quizquestion')

        # Deleting model 'Parameter'
        db.delete_table(u'core_parameter')

        # Deleting model 'ExperimentParameterValue'
        db.delete_table(u'core_experimentparametervalue')

        # Deleting model 'RoundParameterValue'
        db.delete_table(u'core_roundparametervalue')

        # Deleting model 'Group'
        db.delete_table(u'core_group')

        # Deleting model 'GroupCluster'
        db.delete_table(u'core_groupcluster')

        # Deleting model 'GroupRelationship'
        db.delete_table(u'core_grouprelationship')

        # Deleting model 'RoundData'
        db.delete_table(u'core_rounddata')

        # Deleting model 'GroupClusterDataValue'
        db.delete_table(u'core_groupclusterdatavalue')

        # Deleting model 'GroupRoundDataValue'
        db.delete_table(u'core_grouprounddatavalue')

        # Deleting model 'Address'
        db.delete_table(u'core_address')

        # Deleting model 'Participant'
        db.delete_table(u'core_participant')

        # Deleting model 'ParticipantExperimentRelationship'
        db.delete_table(u'core_participantexperimentrelationship')

        # Deleting model 'ParticipantGroupRelationship'
        db.delete_table(u'core_participantgrouprelationship')

        # Deleting model 'ParticipantRoundDataValue'
        db.delete_table(u'core_participantrounddatavalue')

        # Deleting model 'ChatMessage'
        db.delete_table(u'core_chatmessage')

        # Deleting model 'Comment'
        db.delete_table(u'core_comment')

        # Deleting model 'Like'
        db.delete_table(u'core_like')

        # Deleting model 'ActivityLog'
        db.delete_table(u'core_activitylog')

        # Deleting model 'GroupActivityLog'
        db.delete_table(u'core_groupactivitylog')

        # Deleting model 'ExperimentActivityLog'
        db.delete_table(u'core_experimentactivitylog')

        # Deleting model 'ExperimentSession'
        db.delete_table(u'core_experimentsession')

        # Deleting model 'Invitation'
        db.delete_table(u'core_invitation')

        # Deleting model 'ParticipantSignup'
        db.delete_table(u'core_participantsignup')

        # Deleting model 'SpoolParticipantStatistics'
        db.delete_table(u'core_spoolparticipantstatistics')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'core.activitylog': {
            'Meta': {'object_name': 'ActivityLog'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_message': ('django.db.models.fields.TextField', [], {})
        },
        u'core.address': {
            'Meta': {'object_name': 'Address'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'street1': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'street2': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'})
        },
        u'core.chatmessage': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'ChatMessage', '_ormbases': [u'core.ParticipantRoundDataValue']},
            u'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'}),
            'target_participant': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_participant_chat_message_set'", 'null': 'True', 'to': u"orm['core.ParticipantGroupRelationship']"})
        },
        u'core.comment': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'Comment', '_ormbases': [u'core.ParticipantRoundDataValue']},
            u'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'core.experiment': {
            'Meta': {'ordering': "['date_created', 'status']", 'object_name': 'Experiment'},
            'amqp_exchange_name': ('django.db.models.fields.CharField', [], {'default': "'vcweb.default.exchange'", 'max_length': '64'}),
            'authentication_code': ('django.db.models.fields.CharField', [], {'default': "'vcweb.auth.code'", 'max_length': '32'}),
            'current_repeated_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'current_round_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'current_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'current_round_start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentConfiguration']"}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experimenter']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'start_date_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INACTIVE'", 'max_length': '32'}),
            'tick_duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'total_elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        u'core.experimentactivitylog': {
            'Meta': {'object_name': 'ExperimentActivityLog', '_ormbases': [u'core.ActivityLog']},
            u'activitylog_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ActivityLog']", 'unique': 'True', 'primary_key': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log_set'", 'to': u"orm['core.Experiment']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.experimentconfiguration': {
            'Meta': {'ordering': "['experiment_metadata', 'creator', 'date_created']", 'object_name': 'ExperimentConfiguration'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': u"orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': '0.2', 'null': 'True', 'max_digits': '6', 'decimal_places': '2', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': u"orm['core.ExperimentMetadata']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_subject': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'treatment_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'})
        },
        u'core.experimenter': {
            'Meta': {'ordering': "['user']", 'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'experimenter'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
        u'core.experimenterrequest': {
            'Meta': {'object_name': 'ExperimenterRequest'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'core.experimentmetadata': {
            'Meta': {'ordering': "['namespace', 'date_created']", 'object_name': 'ExperimentMetadata'},
            'about_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentConfiguration']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'logo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'namespace': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'short_name': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'core.experimentparametervalue': {
            'Meta': {'object_name': 'ExperimentParameterValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_parameter_value_set'", 'to': u"orm['core.ExperimentConfiguration']"}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.experimentsession': {
            'Meta': {'object_name': 'ExperimentSession'},
            'capacity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': u"orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': u"orm['core.ExperimentMetadata']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateTimeField', [], {}),
            'scheduled_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        u'core.groupactivitylog': {
            'Meta': {'object_name': 'GroupActivityLog', '_ormbases': [u'core.ActivityLog']},
            u'activitylog_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ActivityLog']", 'unique': 'True', 'primary_key': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log_set'", 'to': u"orm['core.Group']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.groupcluster': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'GroupCluster'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        u'core.groupclusterdatavalue': {
            'Meta': {'object_name': 'GroupClusterDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'group_cluster': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.GroupCluster']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_cluster_data_value_set'", 'to': u"orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.grouprelationship': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'GroupRelationship'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_set'", 'to': u"orm['core.GroupCluster']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'core.grouprounddatavalue': {
            'Meta': {'ordering': "['round_data', 'group', 'parameter']", 'object_name': 'GroupRoundDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data_value_set'", 'to': u"orm['core.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_data_value_set'", 'to': u"orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.institution': {
            'Meta': {'object_name': 'Institution'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        u'core.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_session': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentSession']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Participant']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'core.like': {
            'Meta': {'ordering': "['-date_created', 'round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'Like', '_ormbases': [u'core.ParticipantRoundDataValue']},
            u'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'core.parameter': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'experiment_metadata', 'scope'),)", 'object_name': 'Parameter'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_value_string': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'enum_choices': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentMetadata']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'scope': ('django.db.models.fields.CharField', [], {'default': "'round'", 'max_length': '32'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'core.participant': {
            'Meta': {'ordering': "['user']", 'object_name': 'Participant'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Address']", 'null': 'True', 'blank': 'True'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'birthdate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'can_receive_invitations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'experiments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': u"orm['core.ParticipantExperimentRelationship']", 'to': u"orm['core.Experiment']"}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': u"orm['core.ParticipantGroupRelationship']", 'to': u"orm['core.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'participant'", 'unique': 'True', 'to': u"orm['auth.User']"})
        },
        u'core.participantexperimentrelationship': {
            'Meta': {'object_name': 'ParticipantExperimentRelationship'},
            'additional_data': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'current_location': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_relationship_set'", 'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_completed_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_relationship_set'", 'to': u"orm['core.Participant']"}),
            'participant_identifier': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'sequential_participant_identifier': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'core.participantgrouprelationship': {
            'Meta': {'ordering': "['group', 'participant_number']", 'object_name': 'ParticipantGroupRelationship'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'first_visit': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': u"orm['core.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notifications_since': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': u"orm['core.Participant']"}),
            'participant_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'round_joined': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.participantrounddatavalue': {
            'Meta': {'ordering': "['-date_created', 'round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'ParticipantRoundDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'participant_group_relationship': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': u"orm['core.ParticipantGroupRelationship']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': u"orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'submitted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_data_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_data_value_set'", 'null': 'True', 'to': u"orm['core.ParticipantRoundDataValue']"})
        },
        u'core.participantsignup': {
            'Meta': {'object_name': 'ParticipantSignup'},
            'attendance': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': u"orm['core.Invitation']"}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': u"orm['core.Participant']"})
        },
        u'core.quizquestion': {
            'Meta': {'object_name': 'QuizQuestion'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'default_quiz_question_set'", 'null': 'True', 'to': u"orm['core.Experiment']"}),
            'explanation': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'input_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'quiz_question_set'", 'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.roundconfiguration': {
            'Meta': {'ordering': "['experiment_configuration', 'sequence_number', 'date_created']", 'object_name': 'RoundConfiguration'},
            'chat_enabled': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'create_group_clusters': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'debriefing': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_configuration_set'", 'to': u"orm['core.ExperimentConfiguration']"}),
            'group_cluster_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'preserve_existing_groups': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'randomize_groups': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repeat': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'round_type': ('django.db.models.fields.CharField', [], {'default': "'REGULAR'", 'max_length': '32'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'survey_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'template_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        u'core.rounddata': {
            'Meta': {'ordering': "['round_configuration']", 'unique_together': "(('round_configuration', 'experiment'),)", 'object_name': 'RoundData'},
            'elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': u"orm['core.Experiment']"}),
            'experimenter_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.roundparametervalue': {
            'Meta': {'object_name': 'RoundParameterValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_parameter_value_set'", 'to': u"orm['core.RoundConfiguration']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.spoolparticipantstatistics': {
            'Meta': {'object_name': 'SpoolParticipantStatistics'},
            'absences': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'discharges': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitations': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'spool_statistics_set'", 'to': u"orm['core.Participant']"}),
            'participations': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        }
    }

    complete_apps = ['core']