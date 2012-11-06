# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import logging

logger = logging.getLogger(__name__)

class Migration(DataMigration):
    def forwards(self, orm):
        from django.core.management import call_command
        call_command("loaddata", "initial_experiment_metadata.json")
        "Write your forwards methods here."
        # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
        # should probably create a separate data migration for this but I'm lazy
        # create lighter footprints public experiment configuration and experiment
        Activity = orm['lighterprints.Activity']
        Experiment = orm['core.Experiment']
        ExperimentConfiguration = orm['core.ExperimentConfiguration']
        Experimenter = orm['core.Experimenter']
        ExperimentMetadata = orm['core.ExperimentMetadata']
        ParticipantExperimentRelationship = orm['core.ParticipantExperimentRelationship']
        ParticipantGroupRelationship = orm['core.ParticipantGroupRelationship']
        RoundConfiguration = orm['core.RoundConfiguration']
        Parameter = orm['core.Parameter']
        ParticipantRoundDataValue = orm['core.ParticipantRoundDataValue']
        lem = ExperimentMetadata.objects.get(namespace='lighterprints')
        experimenter = Experimenter.objects.get(pk=1)
# create experiment + round configurations
        ec = ExperimentConfiguration.objects.create(experiment_metadata=lem,
                creator=experimenter,
                name="Lighter Footprints Public Challenge",
                is_public=True,
                max_group_size=0)
        rc = RoundConfiguration.objects.create(experiment_configuration=ec, sequence_number=1, display_number=1)
# create experiment instance
        e = Experiment.objects.create(experiment_configuration=ec, experiment_metadata=lem, experimenter=experimenter,
                is_experimenter_driven=False, status='ROUND_IN_PROGRESS', start_date_time=datetime.datetime.now(),
                current_round_start_time=datetime.datetime.now())
# create participant level parameter
        participant_level_param = Parameter.objects.get(name="participant_level")
# create activity unlocked parameter
        activity_unlocked_param = Parameter.objects.get(name="activity_unlocked")
# create round data
        round_data = e.round_data_set.create(round_configuration=rc)
        group = e.group_set.create(number=1, max_size=e.experiment_configuration.max_group_size)
# create group data values for footprint level
        Participant = orm['core.Participant']
        for i, participant in enumerate(Participant.objects.all()):
            ParticipantExperimentRelationship.objects.create(experiment=e, participant=participant,
                    sequential_participant_identifier=i, participant_identifier=i, created_by=experimenter.user)
            # create initial activity unlocked data values
            activity_ids = Activity.objects.filter(name__in=('recycle-paper', 'share-your-ride',
                'enable-sleep-on-computer')).values_list('id', flat=True)
            pgr = ParticipantGroupRelationship.objects.create(participant=participant,
                    group=group,
                    round_joined=rc,
                    participant_number=i + 1)
# create initial participant level data value
            ParticipantRoundDataValue.objects.create(parameter=participant_level_param,
                    participant_group_relationship=pgr, round_data=round_data, int_value=1)
# create initial unlocked activity set data values
            for activity_id in activity_ids:
                ParticipantRoundDataValue.objects.create(parameter=activity_unlocked_param, participant_group_relationship=pgr, round_data=round_data, int_value=activity_id)

    def backwards(self, orm):
        "Write your backwards methods here."

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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'log_message': ('django.db.models.fields.TextField', [], {})
        },
        'core.address': {
            'Meta': {'object_name': 'Address'},
            'city': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'street1': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'street2': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'zipcode': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'})
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'duration': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']"}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentMetadata']"}),
            'experimenter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_experimenter_driven': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_configuration_set'", 'to': "orm['core.ExperimentMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
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
        'core.experimenterrequest': {
            'Meta': {'object_name': 'ExperimenterRequest'},
            'approved': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'core.experimentmetadata': {
            'Meta': {'ordering': "['namespace', 'date_created']", 'object_name': 'ExperimentMetadata'},
            'about_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_configuration': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentConfiguration']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'logo_url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'namespace': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'short_name': ('django.db.models.fields.SlugField', [], {'max_length': '32', 'unique': 'True', 'null': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'core.experimentsession': {
            'Meta': {'object_name': 'ExperimentSession'},
            'capacity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '20'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': "orm['auth.User']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'experiment_session_set'", 'to': "orm['core.ExperimentMetadata']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation_text': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateTimeField', [], {}),
            'scheduled_end_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'data_value_set'", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'group_data_value_set'", 'to': "orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.institution': {
            'Meta': {'object_name': 'Institution'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'core.invitation': {
            'Meta': {'object_name': 'Invitation'},
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'experiment_session': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentSession']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Participant']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'core.like': {
            'Meta': {'ordering': "['-date_created', 'round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'Like', '_ormbases': ['core.ParticipantRoundDataValue']},
            'participantrounddatavalue_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['core.ParticipantRoundDataValue']", 'unique': 'True', 'primary_key': 'True'})
        },
        'core.parameter': {
            'Meta': {'ordering': "['name']", 'unique_together': "(('name', 'experiment_metadata', 'scope'),)", 'object_name': 'Parameter'},
            'class_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Experimenter']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'default_value_string': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'enum_choices': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'experiment_metadata': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.ExperimentMetadata']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'scope': ('django.db.models.fields.CharField', [], {'default': "'round'", 'max_length': '32'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'core.participant': {
            'Meta': {'ordering': "['user']", 'object_name': 'Participant'},
            'address': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Address']", 'null': 'True', 'blank': 'True'}),
            'authentication_token': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'birthdate': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'can_receive_invitations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'experiments': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'participant_set'", 'symmetrical': 'False', 'through': "orm['core.ParticipantExperimentRelationship']", 'to': "orm['core.Experiment']"}),
            'failed_password_attempts': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notifications_since': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_group_relationship_set'", 'to': "orm['core.Participant']"}),
            'participant_number': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'round_joined': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.RoundConfiguration']"})
        },
        'core.participantrounddatavalue': {
            'Meta': {'ordering': "['-date_created', 'round_data', 'participant_group_relationship', 'parameter']", 'object_name': 'ParticipantRoundDataValue'},
            'boolean_value': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'participant_group_relationship': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': "orm['core.ParticipantGroupRelationship']"}),
            'round_data': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'participant_data_value_set'", 'to': "orm['core.RoundData']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'submitted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'target_data_value': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'target_data_value_set'", 'null': 'True', 'to': "orm['core.ParticipantRoundDataValue']"})
        },
        'core.participantsignup': {
            'Meta': {'object_name': 'ParticipantSignup'},
            'attendance': ('django.db.models.fields.PositiveIntegerField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': "orm['core.Invitation']"}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'signup_set'", 'to': "orm['core.Participant']"})
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'debriefing': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'display_number': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'duration': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'experiment_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_configuration_set'", 'to': "orm['core.ExperimentConfiguration']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instructions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
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
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'last_modified': ('vcweb.core.models.AutoDateTimeField', [], {'default': 'datetime.datetime.now'}),
            'parameter': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Parameter']"}),
            'round_configuration': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'round_parameter_value_set'", 'to': "orm['core.RoundConfiguration']"}),
            'string_value': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'core.spoolparticipantstatistics': {
            'Meta': {'object_name': 'SpoolParticipantStatistics'},
            'absences': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'discharges': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invitations': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'participant': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'spool_statistics_set'", 'to': "orm['core.Participant']"}),
            'participations': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'})
        },
        'lighterprints.activity': {
            'Meta': {'ordering': "['level', 'name']", 'object_name': 'Activity'},
            'available_all_day': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cooldown': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True'}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'display_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'group_activity': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'icon': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_modified': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'children_set'", 'null': 'True', 'to': "orm['lighterprints.Activity']"}),
            'personal_benefits': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'points': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'savings': ('django.db.models.fields.DecimalField', [], {'default': '0.0', 'max_digits': '5', 'decimal_places': '2'}),
            'summary': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'lighterprints.activityavailability': {
            'Meta': {'ordering': "['activity', 'start_time']", 'object_name': 'ActivityAvailability'},
            'activity': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'availability_set'", 'to': "orm['lighterprints.Activity']"}),
            'end_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['core', 'lighterprints']
    symmetrical = True
