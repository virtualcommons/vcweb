# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'OstromlabFaqEntry'
        db.create_table(u'core_ostromlabfaqentry', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('question', self.gf('django.db.models.fields.TextField')()),
            ('answer', self.gf('django.db.models.fields.TextField')()),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('vcweb.core.models.AutoDateTimeField')(default=datetime.datetime.now)),
            ('contributor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
        ))
        db.send_create_signal(u'core', ['OstromlabFaqEntry'])


    def backwards(self, orm):
        # Deleting model 'OstromlabFaqEntry'
        db.delete_table(u'core_ostromlabfaqentry')


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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
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
        u'core.bookmarkedexperimentmetadata': {
            'Meta': {'ordering': "['experimenter', 'experiment_metadata']", 'unique_together': "(('experimenter', 'experiment_metadata'),)", 'object_name': 'BookmarkedExperimentMetadata'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookmarked_experiment_metadata_set'", 'to': u"orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bookmarked_experiment_metadata_set'", 'to': u"orm['core.Experimenter']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
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
            'registration_email_subject': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'registration_email_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'INACTIVE'", 'max_length': '32'})
        },
        u'core.experimentactivitylog': {
            'Meta': {'object_name': 'ExperimentActivityLog', '_ormbases': [u'core.ActivityLog']},
            u'activitylog_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['core.ActivityLog']", 'unique': 'True', 'primary_key': 'True'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'activity_log_set'", 'to': u"orm['core.Experiment']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.experimentconfiguration': {
            'Meta': {'ordering': "['experiment_metadata', 'creator', '-date_created']", 'object_name': 'ExperimentConfiguration'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': u"orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': '0.2', 'null': 'True', 'max_digits': '6', 'decimal_places': '2', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': u"orm['core.ExperimentMetadata']"}),
            'has_daily_rounds': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'max_group_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'max_number_of_participants': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'registration_email_subject': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'treatment_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'})
        },
        u'core.experimenter': {
            'Meta': {'ordering': "['user']", 'object_name': 'Experimenter'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'institution_username': ('vcweb.core.models.NullCharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
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
            'location': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateTimeField', [], {}),
            'scheduled_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'blank': 'True'})
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
            'session_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'blank': 'True'})
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
            'acronym': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'cas_server_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
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
        u'core.ostromlabfaqentry': {
            'Meta': {'object_name': 'OstromlabFaqEntry'},
            'answer': ('django.db.models.fields.TextField', [], {}),
            'contributor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'question': ('django.db.models.fields.TextField', [], {})
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
            'class_status': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': u"orm['core.ParticipantExperimentRelationship']", 'to': u"orm['core.Experiment']"}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'favorite_color': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'favorite_food': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'favorite_movie_genre': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'favorite_sport': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': u"orm['core.ParticipantGroupRelationship']", 'to': u"orm['core.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'institution': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Institution']", 'null': 'True', 'blank': 'True'}),
            'institution_username': ('vcweb.core.models.NullCharField', [], {'max_length': '64', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'major': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
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
            'round_joined': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.RoundConfiguration']"}),
            'survey_completed': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
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
            'attendance': ('django.db.models.fields.PositiveIntegerField', [], {'default': '3', 'max_length': '1'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': u"orm['core.Invitation']"})
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
            'initialize_data_values': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'instructions': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'preserve_existing_groups': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'randomize_groups': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repeat': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'round_type': ('django.db.models.fields.CharField', [], {'default': "'REGULAR'", 'max_length': '32'}),
            'sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '64', 'blank': 'True'}),
            'survey_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'template_filename': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'template_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'})
        },
        u'core.rounddata': {
            'Meta': {'ordering': "['round_configuration', 'repeating_round_sequence_number']", 'unique_together': "(('round_configuration', 'repeating_round_sequence_number', 'experiment'),)", 'object_name': 'RoundData'},
            'elapsed_time': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': u"orm['core.Experiment']"}),
            'experimenter_notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'repeating_round_sequence_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_data_set'", 'to': u"orm['core.RoundConfiguration']"})
        },
        u'core.roundparametervalue': {
            'Meta': {'ordering': "['round_configuration', 'parameter', 'date_created']", 'object_name': 'RoundParameterValue'},
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