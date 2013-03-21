# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'GreenButtonIntervalBlock'
        db.create_table(u'lighterprints_greenbuttonintervalblock', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('participant_group_relationship', self.gf('django.db.models.fields.related.ForeignKey')(related_name='gb_interval_block_set', to=orm['core.ParticipantGroupRelationship'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('start', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('total_duration', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal(u'lighterprints', ['GreenButtonIntervalBlock'])

        # Adding model 'GreenButtonIntervalReading'
        db.create_table(u'lighterprints_greenbuttonintervalreading', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('interval_block', self.gf('django.db.models.fields.related.ForeignKey')(related_name='interval_reading_set', to=orm['lighterprints.GreenButtonIntervalBlock'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('seconds_from_epoch', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('watt_hours', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('millicents', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'lighterprints', ['GreenButtonIntervalReading'])

        # Adding model 'Activity'
        db.create_table(u'lighterprints_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
            ('display_name', self.gf('django.db.models.fields.CharField')(max_length=64, null=True, blank=True)),
            ('summary', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('url', self.gf('django.db.models.fields.URLField')(max_length=200)),
            ('savings', self.gf('django.db.models.fields.DecimalField')(default=0.0, max_digits=5, decimal_places=2)),
            ('points', self.gf('django.db.models.fields.PositiveIntegerField')(default=0)),
            ('available_all_day', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('personal_benefits', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('level', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('group_activity', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('cooldown', self.gf('django.db.models.fields.PositiveIntegerField')(default=1, null=True, blank=True)),
            ('icon', self.gf('django.db.models.fields.files.ImageField')(max_length=100)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('last_modified', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('parent', self.gf('mptt.fields.TreeForeignKey')(blank=True, related_name='children_set', null=True, to=orm['lighterprints.Activity'])),
            ('is_public', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('lft', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('rght', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
            ('tree_id', self.gf('django.db.models.fields.PositiveIntegerField')(db_index=True)),
        ))
        db.send_create_signal(u'lighterprints', ['Activity'])

        # Adding model 'ActivityAvailability'
        db.create_table(u'lighterprints_activityavailability', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('activity', self.gf('django.db.models.fields.related.ForeignKey')(related_name='availability_set', to=orm['lighterprints.Activity'])),
            ('start_time', self.gf('django.db.models.fields.TimeField')(null=True, blank=True)),
            ('end_time', self.gf('django.db.models.fields.TimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'lighterprints', ['ActivityAvailability'])


    def backwards(self, orm):
        # Deleting model 'GreenButtonIntervalBlock'
        db.delete_table(u'lighterprints_greenbuttonintervalblock')

        # Deleting model 'GreenButtonIntervalReading'
        db.delete_table(u'lighterprints_greenbuttonintervalreading')

        # Deleting model 'Activity'
        db.delete_table(u'lighterprints_activity')

        # Deleting model 'ActivityAvailability'
        db.delete_table(u'lighterprints_activityavailability')


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
        u'core.address': {
            'Meta': {'object_name': 'Address'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'street1': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'street2': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'})
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
        u'core.group': {
            'Meta': {'ordering': "['experiment', 'number']", 'object_name': 'Group'},
            'experiment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['core.Experiment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_size': ('django.db.models.fields.PositiveIntegerField', [], {'default': '5'}),
            'number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'session_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
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
        u'lighterprints.activity': {
            'Meta': {'ordering': "['level', 'name']", 'object_name': 'Activity'},
            'available_all_day': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cooldown': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'group_activity': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children_set'", 'null': 'True', 'to': u"orm['lighterprints.Activity']"}),
            'personal_benefits': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'points': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'savings': ('django.db.models.fields.DecimalField', [], {'default': '0.0', 'max_digits': '5', 'decimal_places': '2'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        u'lighterprints.activityavailability': {
            'Meta': {'ordering': "['activity', 'start_time']", 'object_name': 'ActivityAvailability'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'availability_set'", 'to': u"orm['lighterprints.Activity']"}),
            'end_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'lighterprints.greenbuttonintervalblock': {
            'Meta': {'object_name': 'GreenButtonIntervalBlock'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant_group_relationship': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'gb_interval_block_set'", 'to': u"orm['core.ParticipantGroupRelationship']"}),
            'start': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'total_duration': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'lighterprints.greenbuttonintervalreading': {
            'Meta': {'object_name': 'GreenButtonIntervalReading'},
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'interval_block': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'interval_reading_set'", 'to': u"orm['lighterprints.GreenButtonIntervalBlock']"}),
            'millicents': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'seconds_from_epoch': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'watt_hours': ('django.db.models.fields.PositiveIntegerField', [], {})
        }
    }

    complete_apps = ['lighterprints']