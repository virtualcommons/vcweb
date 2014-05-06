# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'GroupClusterDataValue.string_value'
        db.alter_column(u'core_groupclusterdatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'GroupRoundDataValue.string_value'
        db.alter_column(u'core_grouprounddatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'Institution.description'
        db.alter_column(u'core_institution', 'description', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'Experimenter.authentication_token'
        db.alter_column(u'core_experimenter', 'authentication_token', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'Parameter.display_name'
        db.alter_column(u'core_parameter', 'display_name', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

        # Changing field 'Parameter.description'
        db.alter_column(u'core_parameter', 'description', self.gf('django.db.models.fields.CharField')(default='', max_length=512))

        # Changing field 'Parameter.class_name'
        db.alter_column(u'core_parameter', 'class_name', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'Parameter.default_value_string'
        db.alter_column(u'core_parameter', 'default_value_string', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

        # Changing field 'Parameter.enum_choices'
        db.alter_column(u'core_parameter', 'enum_choices', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'ParticipantExperimentRelationship.current_location'
        db.alter_column(u'core_participantexperimentrelationship', 'current_location', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'ParticipantExperimentRelationship.additional_data'
        db.alter_column(u'core_participantexperimentrelationship', 'additional_data', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'Group.session_id'
        db.alter_column(u'core_group', 'session_id', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'RoundConfiguration.debriefing'
        db.alter_column(u'core_roundconfiguration', 'debriefing', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'RoundConfiguration.template_filename'
        db.alter_column(u'core_roundconfiguration', 'template_filename', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'RoundConfiguration.session_id'
        db.alter_column(u'core_roundconfiguration', 'session_id', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'RoundConfiguration.template_id'
        db.alter_column(u'core_roundconfiguration', 'template_id', self.gf('django.db.models.fields.CharField')(default='', max_length=128))

        # Changing field 'RoundConfiguration.instructions'
        db.alter_column(u'core_roundconfiguration', 'instructions', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'ExperimentSession.invitation_text'
        db.alter_column(u'core_experimentsession', 'invitation_text', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'RoundParameterValue.string_value'
        db.alter_column(u'core_roundparametervalue', 'string_value', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'ParticipantRoundDataValue.string_value'
        db.alter_column(u'core_participantrounddatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'Participant.authentication_token'
        db.alter_column(u'core_participant', 'authentication_token', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'ExperimentMetadata.description'
        db.alter_column(u'core_experimentmetadata', 'description', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'Experiment.tick_duration'
        db.alter_column(u'core_experiment', 'tick_duration', self.gf('django.db.models.fields.CharField')(default='', max_length=32))

        # Changing field 'Experiment.duration'
        db.alter_column(u'core_experiment', 'duration', self.gf('django.db.models.fields.CharField')(default='', max_length=32))

        # Changing field 'ExperimentParameterValue.string_value'
        db.alter_column(u'core_experimentparametervalue', 'string_value', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'GroupCluster.session_id'
        db.alter_column(u'core_groupcluster', 'session_id', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'GroupCluster.name'
        db.alter_column(u'core_groupcluster', 'name', self.gf('django.db.models.fields.CharField')(default='', max_length=64))

        # Changing field 'ExperimentConfiguration.invitation_text'
        db.alter_column(u'core_experimentconfiguration', 'invitation_text', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'ExperimentConfiguration.treatment_id'
        db.alter_column(u'core_experimentconfiguration', 'treatment_id', self.gf('django.db.models.fields.CharField')(default='', max_length=32))

        # Changing field 'ExperimentConfiguration.invitation_subject'
        db.alter_column(u'core_experimentconfiguration', 'invitation_subject', self.gf('django.db.models.fields.TextField')(default=''))

        # Changing field 'RoundData.experimenter_notes'
        db.alter_column(u'core_rounddata', 'experimenter_notes', self.gf('django.db.models.fields.TextField')(default=''))

    def backwards(self, orm):

        # Changing field 'GroupClusterDataValue.string_value'
        db.alter_column(u'core_groupclusterdatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'GroupRoundDataValue.string_value'
        db.alter_column(u'core_grouprounddatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Institution.description'
        db.alter_column(u'core_institution', 'description', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Experimenter.authentication_token'
        db.alter_column(u'core_experimenter', 'authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'Parameter.display_name'
        db.alter_column(u'core_parameter', 'display_name', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Parameter.description'
        db.alter_column(u'core_parameter', 'description', self.gf('django.db.models.fields.CharField')(max_length=512, null=True))

        # Changing field 'Parameter.class_name'
        db.alter_column(u'core_parameter', 'class_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'Parameter.default_value_string'
        db.alter_column(u'core_parameter', 'default_value_string', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

        # Changing field 'Parameter.enum_choices'
        db.alter_column(u'core_parameter', 'enum_choices', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'ParticipantExperimentRelationship.current_location'
        db.alter_column(u'core_participantexperimentrelationship', 'current_location', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'ParticipantExperimentRelationship.additional_data'
        db.alter_column(u'core_participantexperimentrelationship', 'additional_data', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Group.session_id'
        db.alter_column(u'core_group', 'session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'RoundConfiguration.debriefing'
        db.alter_column(u'core_roundconfiguration', 'debriefing', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'RoundConfiguration.template_filename'
        db.alter_column(u'core_roundconfiguration', 'template_filename', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'RoundConfiguration.session_id'
        db.alter_column(u'core_roundconfiguration', 'session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'RoundConfiguration.template_id'
        db.alter_column(u'core_roundconfiguration', 'template_id', self.gf('django.db.models.fields.CharField')(max_length=128, null=True))

        # Changing field 'RoundConfiguration.instructions'
        db.alter_column(u'core_roundconfiguration', 'instructions', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'ExperimentSession.invitation_text'
        db.alter_column(u'core_experimentsession', 'invitation_text', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'RoundParameterValue.string_value'
        db.alter_column(u'core_roundparametervalue', 'string_value', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'ParticipantRoundDataValue.string_value'
        db.alter_column(u'core_participantrounddatavalue', 'string_value', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Participant.authentication_token'
        db.alter_column(u'core_participant', 'authentication_token', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'ExperimentMetadata.description'
        db.alter_column(u'core_experimentmetadata', 'description', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'Experiment.tick_duration'
        db.alter_column(u'core_experiment', 'tick_duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))

        # Changing field 'Experiment.duration'
        db.alter_column(u'core_experiment', 'duration', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))

        # Changing field 'ExperimentParameterValue.string_value'
        db.alter_column(u'core_experimentparametervalue', 'string_value', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'GroupCluster.session_id'
        db.alter_column(u'core_groupcluster', 'session_id', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'GroupCluster.name'
        db.alter_column(u'core_groupcluster', 'name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True))

        # Changing field 'ExperimentConfiguration.invitation_text'
        db.alter_column(u'core_experimentconfiguration', 'invitation_text', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'ExperimentConfiguration.treatment_id'
        db.alter_column(u'core_experimentconfiguration', 'treatment_id', self.gf('django.db.models.fields.CharField')(max_length=32, null=True))

        # Changing field 'ExperimentConfiguration.invitation_subject'
        db.alter_column(u'core_experimentconfiguration', 'invitation_subject', self.gf('django.db.models.fields.TextField')(null=True))

        # Changing field 'RoundData.experimenter_notes'
        db.alter_column(u'core_rounddata', 'experimenter_notes', self.gf('django.db.models.fields.TextField')(null=True))

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
            'Meta': {'ordering': "['-date_created']", 'object_name': 'ChatMessage', '_ormbases': [u'core.ParticipantRoundDataValue']},
            u'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'}),
            'target_participant': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_participant_chat_message_set'", 'null': 'True', 'to': u"orm['core.ParticipantGroupRelationship']"})
        },
        u'core.comment': {
            'Meta': {'ordering': "['-date_created']", 'object_name': 'Comment', '_ormbases': [u'core.ParticipantRoundDataValue']},
            u'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'core.experiment': {
            'Meta': {'ordering': "['date_created', 'status']", 'object_name': 'Experiment'},
            'amqp_exchange_name': ('django.db.models.fields.CharField', [], {'default': "'vcweb.default.exchange'", 'max_length': '64'}),
            'authentication_code': ('django.db.models.fields.CharField', [], {'default': "'vcweb.auth.code'", 'max_length': '32'}),
            'current_repeated_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'current_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'current_round_start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_activated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentConfiguration']"}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experimenter']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INACTIVE'", 'max_length': '32'}),
            'tick_duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'})
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
            'invitation_subject': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'treatment_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'})
        },
        u'core.experimenter': {
            'Meta': {'ordering': "['user']", 'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
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
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
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
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameter_value_set'", 'to': u"orm['core.ExperimentConfiguration']"}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'core.experimentsession': {
            'Meta': {'object_name': 'ExperimentSession'},
            'capacity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': u"orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': u"orm['core.ExperimentMetadata']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateTimeField', [], {}),
            'scheduled_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
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
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_cluster_set'", 'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'})
        },
        u'core.groupclusterdatavalue': {
            'Meta': {'object_name': 'GroupClusterDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'group_cluster': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data_value_set'", 'to': u"orm['core.GroupCluster']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Parameter']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_cluster_data_value_set'", 'to': u"orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'core.grouprelationship': {
            'Meta': {'ordering': "['date_created']", 'object_name': 'GroupRelationship'},
            'cluster': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_relationship_set'", 'to': u"orm['core.GroupCluster']"}),
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
            'string_value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        },
        u'core.institution': {
            'Meta': {'object_name': 'Institution'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
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
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_value_string': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'enum_choices': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
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
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
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
            'additional_data': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'current_location': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
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
            'participant_group_relationship': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data_value_set'", 'to': u"orm['core.ParticipantGroupRelationship']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': u"orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
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
            'debriefing': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'display_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_configuration_set'", 'to': u"orm['core.ExperimentConfiguration']"}),
            'group_cluster_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '2', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'preserve_existing_groups': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'randomize_groups': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repeat': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'round_type': ('django.db.models.fields.CharField', [], {'default': "'REGULAR'", 'max_length': '32'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'survey_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'template_filename': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'template_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'})
        },
        u'core.rounddata': {
            'Meta': {'ordering': "['round_configuration']", 'unique_together': "(('round_configuration', 'repeating_round_sequence_number', 'experiment'),)", 'object_name': 'RoundData'},
            'elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': u"orm['core.Experiment']"}),
            'experimenter_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'repeating_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
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
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parameter_value_set'", 'to': u"orm['core.RoundConfiguration']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'blank': 'True'})
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