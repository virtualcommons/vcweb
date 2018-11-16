# -*- coding: utf-8 -*-


from django.db import models, migrations
import datetime
import vcweb.core.models
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('log_message', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('street1', models.CharField(
                    max_length=256, verbose_name='Street')),
                ('street2', models.CharField(
                    max_length=256, verbose_name='Street')),
                ('city', models.CharField(
                    max_length=128, verbose_name='City', blank=True)),
                ('state', models.CharField(
                    max_length=128, verbose_name='State', blank=True)),
                ('zipcode', models.CharField(
                    max_length=8, verbose_name='Zip code', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BookmarkedExperimentMetadata',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['experimenter', 'experiment_metadata'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Experiment',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('authentication_code', models.CharField(
                    default=b'vcweb.auth.code', max_length=32)),
                ('current_round_sequence_number', models.PositiveIntegerField(
                    default=1, help_text='One-based sequence number used to identify which round the experiment is currently running')),
                ('current_repeated_round_sequence_number', models.PositiveIntegerField(
                    default=0, help_text='The number of times this round has been repeated')),
                ('status', models.CharField(default=b'INACTIVE', max_length=32, choices=[(b'INACTIVE', 'Not active'), (
                    b'ACTIVE', 'Active, no round in progress'), (b'ROUND_IN_PROGRESS', 'Round in progress'), (b'COMPLETED', 'Completed')])),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('date_activated', models.DateTimeField(
                    null=True, blank=True)),
                ('duration', models.CharField(
                    help_text='Duration of the experiment', max_length=32, blank=True)),
                ('start_date', models.DateField(
                    help_text='Signifies that the experiment should activate automatically on the specified date.', null=True, blank=True)),
                ('current_round_start_time',
                 models.DateTimeField(null=True, blank=True)),
                ('registration_email_subject', models.CharField(
                    help_text='email subject header on registration emails sent to a participant', max_length=128, blank=True)),
                ('registration_email_text', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['date_created', 'status'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimentActivityLog',
            fields=[
                ('activitylog_ptr', models.OneToOneField(
                    parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.ActivityLog')),
                ('experiment', models.ForeignKey(
                    related_name=b'activity_log_set', to='core.Experiment')),
            ],
            options={
            },
            bases=('core.activitylog',),
        ),
        migrations.CreateModel(
            name='ExperimentConfiguration',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('max_number_of_participants',
                 models.PositiveIntegerField(default=0)),
                ('registration_email_subject', models.TextField(
                    help_text='Subject header for email registrations', blank=True)),
                ('invitation_text', models.TextField(
                    help_text='Text to send out via email invitations', blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_public', models.BooleanField(default=False)),
                ('max_group_size', models.PositiveIntegerField(default=5)),
                ('exchange_rate', models.DecimalField(decimal_places=2, default=0.2, max_digits=6, blank=True,
                                                      help_text='Exchange rate of currency per in-game token, dollars per token', null=True)),
                ('show_up_payment', models.DecimalField(decimal_places=2, default=5.0, max_digits=6, blank=True,
                                                        help_text='Show up fee paid to an in-lab experiment participant for showing up', null=True)),
                ('maximum_payment', models.DecimalField(decimal_places=2, default=40.0, max_digits=6, blank=True,
                                                        help_text='Maximum amount a participant expects to be paid for this experiment', null=True)),
                ('treatment_id', models.CharField(
                    help_text='Alphanumeric ID unique over the set of ExperimentConfigurations in a given ExperimentMetadata', max_length=32, blank=True)),
                ('is_experimenter_driven', models.BooleanField(
                    default=True, help_text='Experimenter explicitly advances the experiment to the next round.')),
                ('has_daily_rounds', models.BooleanField(
                    default=False, help_text='This experiment configuration has rounds that start and end each day starting at midnight.')),
            ],
            options={
                'ordering': ['experiment_metadata', 'creator', '-date_created'],
            },
            bases=(models.Model, vcweb.core.models.ParameterValueMixin),
        ),
        migrations.CreateModel(
            name='Experimenter',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('failed_password_attempts',
                 models.PositiveIntegerField(default=0)),
                ('authentication_token', models.CharField(
                    max_length=64, blank=True)),
                ('approved', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['user'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimenterRequest',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('approved', models.BooleanField(default=False)),
                ('user', models.OneToOneField(
                    verbose_name='Django User', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimentMetadata',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255)),
                ('namespace', models.CharField(blank=True, max_length=255, unique=True,
                                               null=True, validators=[django.core.validators.RegexValidator(b'^[\\w_-]*$')])),
                ('short_name', models.SlugField(
                    max_length=32, unique=True, null=True, blank=True)),
                ('description', models.TextField(blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('about_url', models.URLField(null=True, blank=True)),
                ('logo_url', models.URLField(null=True, blank=True)),
                ('active', models.BooleanField(default=True)),
                ('default_configuration', models.ForeignKey(
                    blank=True, to='core.ExperimentConfiguration', null=True)),
            ],
            options={
                'ordering': ['title', 'namespace'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimentParameterValue',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('string_value', models.TextField(blank=True)),
                ('int_value', models.IntegerField(null=True, blank=True)),
                ('float_value', models.FloatField(null=True, blank=True)),
                ('boolean_value', models.NullBooleanField()),
                ('date_created', models.DateTimeField(
                    auto_now_add=True, db_index=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('experiment_configuration', models.ForeignKey(
                    related_name=b'parameter_value_set', to='core.ExperimentConfiguration')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExperimentSession',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('scheduled_date', models.DateTimeField()),
                ('scheduled_end_date', models.DateTimeField(
                    null=True, blank=True)),
                ('capacity', models.PositiveIntegerField(default=20)),
                ('location', models.CharField(
                    help_text='Where will this experiment session be held?', max_length=128, blank=True)),
                ('invitation_text', models.TextField(blank=True)),
                ('creator', models.ForeignKey(
                    related_name=b'experiment_session_set', to=settings.AUTH_USER_MODEL)),
                ('experiment_metadata', models.ForeignKey(
                    related_name=b'experiment_session_set', to='core.ExperimentMetadata')),
            ],
            options={
                'ordering': ['scheduled_date'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Group',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.PositiveIntegerField()),
                ('max_size', models.PositiveIntegerField(default=5)),
                ('session_id', models.CharField(
                    default=b'', max_length=64, blank=True)),
                ('experiment', models.ForeignKey(to='core.Experiment')),
            ],
            options={
                'ordering': ['experiment', 'number'],
            },
            bases=(models.Model, vcweb.core.models.DataValueMixin),
        ),
        migrations.CreateModel(
            name='GroupActivityLog',
            fields=[
                ('activitylog_ptr', models.OneToOneField(
                    parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.ActivityLog')),
                ('group', models.ForeignKey(
                    related_name=b'activity_log_set', to='core.Group')),
            ],
            options={
            },
            bases=('core.activitylog',),
        ),
        migrations.CreateModel(
            name='GroupCluster',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=64, blank=True)),
                ('session_id', models.CharField(
                    default=b'', max_length=64, blank=True)),
                ('experiment', models.ForeignKey(
                    related_name=b'group_cluster_set', to='core.Experiment')),
            ],
            options={
                'ordering': ['date_created'],
            },
            bases=(models.Model, vcweb.core.models.DataValueMixin),
        ),
        migrations.CreateModel(
            name='GroupClusterDataValue',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('string_value', models.TextField(blank=True)),
                ('int_value', models.IntegerField(null=True, blank=True)),
                ('float_value', models.FloatField(null=True, blank=True)),
                ('boolean_value', models.NullBooleanField()),
                ('date_created', models.DateTimeField(
                    auto_now_add=True, db_index=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('group_cluster', models.ForeignKey(
                    related_name=b'data_value_set', to='core.GroupCluster')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupRelationship',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('cluster', models.ForeignKey(
                    related_name=b'group_relationship_set', to='core.GroupCluster')),
                ('group', models.ForeignKey(
                    related_name=b'relationship_set', to='core.Group')),
            ],
            options={
                'ordering': ['date_created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupRoundDataValue',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('string_value', models.TextField(blank=True)),
                ('int_value', models.IntegerField(null=True, blank=True)),
                ('float_value', models.FloatField(null=True, blank=True)),
                ('boolean_value', models.NullBooleanField()),
                ('date_created', models.DateTimeField(
                    auto_now_add=True, db_index=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('group', models.ForeignKey(
                    related_name=b'data_value_set', to='core.Group')),
            ],
            options={
                'ordering': ['round_data', 'group', 'parameter'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('acronym', models.CharField(max_length=16, blank=True)),
                ('description', models.TextField(blank=True)),
                ('url', models.URLField(null=True, blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('cas_server_url', models.URLField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invitation',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('experiment_session', models.ForeignKey(
                    to='core.ExperimentSession')),
            ],
            options={
                'ordering': ['experiment_session', 'date_created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OstromlabFaqEntry',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('question', models.TextField(help_text='FAQ Question')),
                ('answer', models.TextField(help_text='FAQ Answer')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('contributor', models.ForeignKey(
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['question', '-date_created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Parameter',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scope', models.CharField(default=b'round', max_length=32, choices=[(b'round', b'Round configuration data applicable to all groups for a given round'), (b'experiment', b'Experiment configuration data relevant to the entire experiment'), (
                    b'group', b'Group data for a given group in a given round'), (b'group_cluster', b'Group cluster data for a given group cluster in a given round'), (b'participant', b'Participant data for a given participant in a given round')])),
                ('name', models.CharField(unique=True, max_length=255)),
                ('display_name', models.CharField(
                    default=b'', max_length=255, blank=True)),
                ('description', models.CharField(
                    default=b'', max_length=512, blank=True)),
                ('type', models.CharField(max_length=32, choices=[(b'int', b'Integer value'), (b'string', b'String value'), (b'foreignkey', b'Foreign key'), (
                    b'float', b'Floating-point number'), (b'boolean', b'Boolean value (true/false)'), (b'enum', b'Enumeration')])),
                ('class_name', models.CharField(
                    help_text=b'Model classname in the form of appname.modelname, e.g., "core.Experiment".  Only applicable for foreign key parameters.', max_length=64, blank=True)),
                ('default_value_string', models.CharField(
                    max_length=255, blank=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('enum_choices', models.TextField(blank=True)),
                ('is_required', models.BooleanField(default=False)),
                ('creator', models.ForeignKey(
                    blank=True, to='core.Experimenter', null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('failed_password_attempts',
                 models.PositiveIntegerField(default=0)),
                ('authentication_token', models.CharField(
                    max_length=64, blank=True)),
                ('can_receive_invitations', models.BooleanField(
                    default=False, help_text="Check this box if you'd like to opt-in and receive email invitations for upcoming experiments")),
                ('gender', models.CharField(
                    blank=True, max_length=1, choices=[(b'M', b'Male'), (b'F', b'Female')])),
                ('birthdate', models.DateField(null=True, blank=True)),
                ('major', models.CharField(max_length=128, blank=True)),
                ('class_status', models.CharField(blank=True, max_length=32, choices=[(b'Freshman', b'Freshman'), (b'Sophomore', b'Sophomore'), (
                    b'Junior', b'Junior'), (b'Senior', b'Senior'), (b'Graduate', b'Graduate'), (b'Other', b'Other')])),
                ('favorite_sport', models.CharField(blank=True, max_length=32, choices=[
                 (b'Football', b'Football'), (b'Baseball', b'Baseball'), (b'Hockey', b'Hockey'), (b'Basketball', b'Basketball'), (b'Other', b'Other')])),
                ('favorite_color', models.CharField(blank=True, max_length=32, choices=[(b'red', b'red'), (b'blue', b'blue'), (b'green', b'green'), (
                    b'yellow', b'yellow'), (b'black', b'black'), (b'white', b'white'), (b'pink', b'pink'), (b'purple', b'purple'), (b'other', b'other')])),
                ('favorite_food', models.CharField(blank=True, max_length=32, choices=[
                 (b'Fast food', b'Fast food'), (b'Haute cuisine', b'Haute cuisine'), (b'Asian', b'Asian'), (b'Mexican', b'Mexican'), (b'Other', b'Other')])),
                ('favorite_movie_genre', models.CharField(blank=True, max_length=64, choices=[(b'Family', b'Family'), (b'Action', b'Action'), (b'Comedy', b'Comedy'), (b'Science Fiction', b'Science Fiction'), (b'Documentary', b'Documentary'), (
                    b'Cult', b'Cult'), (b'Sport', b'Sport'), (b'Musical', b'Musical'), (b'Horror', b'Horror'), (b'Foreign', b'Foreign'), (b'Romance', b'Romance'), (b'Independent', b'Independent'), (b'Drama', b'Drama')])),
                ('address', models.ForeignKey(
                    blank=True, to='core.Address', null=True)),
            ],
            options={
                'ordering': ['user'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ParticipantExperimentRelationship',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('participant_identifier', models.CharField(max_length=32)),
                ('sequential_participant_identifier',
                 models.PositiveIntegerField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_completed_round_sequence_number',
                 models.PositiveIntegerField(default=0)),
                ('current_location', models.CharField(
                    max_length=64, blank=True)),
                ('additional_data', models.TextField(blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('experiment', models.ForeignKey(
                    related_name=b'participant_relationship_set', to='core.Experiment')),
                ('participant', models.ForeignKey(
                    related_name=b'experiment_relationship_set', to='core.Participant')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ParticipantGroupRelationship',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('participant_number', models.PositiveIntegerField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('active', models.BooleanField(default=True)),
                ('first_visit', models.BooleanField(default=True)),
                ('notifications_since', models.DateTimeField(
                    default=datetime.datetime.now, null=True, blank=True)),
                ('survey_completed', models.BooleanField(default=False)),
                ('group', models.ForeignKey(
                    related_name=b'participant_group_relationship_set', to='core.Group')),
                ('participant', models.ForeignKey(
                    related_name=b'participant_group_relationship_set', to='core.Participant')),
            ],
            options={
                'ordering': ['group', 'participant_number'],
            },
            bases=(models.Model, vcweb.core.models.DataValueMixin),
        ),
        migrations.CreateModel(
            name='ParticipantRoundDataValue',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('string_value', models.TextField(blank=True)),
                ('int_value', models.IntegerField(null=True, blank=True)),
                ('float_value', models.FloatField(null=True, blank=True)),
                ('boolean_value', models.NullBooleanField()),
                ('date_created', models.DateTimeField(
                    auto_now_add=True, db_index=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('submitted', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-date_created', 'round_data', 'participant_group_relationship', 'parameter'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Like',
            fields=[
                ('participantrounddatavalue_ptr', models.OneToOneField(
                    parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.ParticipantRoundDataValue')),
            ],
            options={
                'abstract': False,
            },
            bases=('core.participantrounddatavalue',),
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('participantrounddatavalue_ptr', models.OneToOneField(
                    parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.ParticipantRoundDataValue')),
            ],
            options={
                'ordering': ['-date_created'],
            },
            bases=('core.participantrounddatavalue',),
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('participantrounddatavalue_ptr', models.OneToOneField(
                    parent_link=True, auto_created=True, primary_key=True, serialize=False, to='core.ParticipantRoundDataValue')),
            ],
            options={
                'ordering': ['-date_created'],
            },
            bases=('core.participantrounddatavalue',),
        ),
        migrations.CreateModel(
            name='ParticipantSignup',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('attendance', models.PositiveIntegerField(
                    default=3, max_length=1, choices=[(0, 'participated'), (1, 'turned away'), (2, 'absent'), (3, 'signed up')])),
                ('invitation', models.ForeignKey(
                    related_name=b'signup_set', to='core.Invitation')),
            ],
            options={
                'ordering': ['invitation__experiment_session'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RoundConfiguration',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('sequence_number', models.PositiveIntegerField(
                    help_text='Determines the ordering of the rounds in an experiment in ascending order, e.g., 1,2,3,4,5')),
                ('display_number', models.PositiveIntegerField(
                    default=0, help_text='Display round number, defaults to sequence_number if 0.')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('duration', models.PositiveIntegerField(
                    default=0, help_text='Duration in seconds. 0 signifies an untimed round only advanced by an experimenter.')),
                ('instructions', models.TextField(blank=True)),
                ('debriefing', models.TextField(blank=True)),
                ('round_type', models.CharField(default=b'REGULAR', max_length=32, choices=[(b'WELCOME', 'Initial welcome page'), (b'GENERAL_INSTRUCTIONS', 'General introduction'), (b'REGULAR', 'Regular experiment round'), (
                    b'CHAT', 'Communication round'), (b'DEBRIEFING', 'Debriefing round summary'), (b'INSTRUCTIONS', 'Instructions'), (b'PRACTICE', 'Practice round'), (b'QUIZ', 'Quiz round'), (b'SURVEY', 'Survey round')])),
                ('template_filename', models.CharField(
                    help_text='The filename of the template to use to render when executing this round.\n                        This file should exist in your templates directory as your-experiment-namespace/template-name.html,\n                        e.g., if set to foo.html, vcweb will look for templates/forestry/foo.html', max_length=64, blank=True)),
                ('template_id', models.CharField(
                    help_text='A HTML template ID to use in a single page app, e.g., KO template', max_length=128, blank=True)),
                ('survey_url', models.URLField(null=True, blank=True)),
                ('chat_enabled', models.BooleanField(
                    default=False, help_text='Enable in-round communication')),
                ('create_group_clusters', models.BooleanField(
                    default=False, help_text='Create relationships (clusters) of groups that can share group cluster data values')),
                ('group_cluster_size', models.PositiveIntegerField(
                    default=2, help_text='How many groups should form a cluster?', null=True, blank=True)),
                ('randomize_groups', models.BooleanField(
                    default=False, help_text='Shuffle participants into new groups when the round begins?')),
                ('preserve_existing_groups', models.BooleanField(
                    default=True, help_text='This option is only useful if randomize_groups is set to true.  If we are randomizing groups, should existing groups (if any) be preserved?')),
                ('session_id', models.CharField(
                    default=b'', help_text="\n            Session id to associate with this round data and the groups in this experiment, useful for longer\n            multi-session experiments where group membership may change.  We don't want to destroy the old groups as\n            that information is still needed to determine payments, etc. Instead we need to create a new set of\n            Group/ParticipantGroupRelationship models that can live in conjunction with the existing\n            Group/ParticipantGroupRelationship models.\n            ", max_length=64, blank=True)),
                ('repeat', models.PositiveIntegerField(
                    default=0, help_text='If set to a positive integer n, this round will repeat itself n times with the same configuration and parameter values.')),
                ('initialize_data_values', models.BooleanField(
                    default=False, help_text='Re-initialize all group and participant parameters at the start of this round.  ')),
                ('experiment_configuration', models.ForeignKey(
                    related_name=b'round_configuration_set', to='core.ExperimentConfiguration')),
            ],
            options={
                'ordering': ['experiment_configuration', 'sequence_number', 'date_created'],
            },
            bases=(models.Model, vcweb.core.models.ParameterValueMixin),
        ),
        migrations.CreateModel(
            name='RoundData',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('repeating_round_sequence_number', models.PositiveIntegerField(
                    default=0, help_text='Sequence number used to disambiguate round data in repeating rounds')),
                ('elapsed_time', models.PositiveIntegerField(default=0)),
                ('experimenter_notes', models.TextField(blank=True)),
                ('experiment', models.ForeignKey(
                    related_name=b'round_data_set', to='core.Experiment')),
                ('round_configuration', models.ForeignKey(
                    related_name=b'round_data_set', to='core.RoundConfiguration')),
            ],
            options={
                'ordering': ['round_configuration', 'repeating_round_sequence_number'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RoundParameterValue',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('string_value', models.TextField(blank=True)),
                ('int_value', models.IntegerField(null=True, blank=True)),
                ('float_value', models.FloatField(null=True, blank=True)),
                ('boolean_value', models.NullBooleanField()),
                ('date_created', models.DateTimeField(
                    auto_now_add=True, db_index=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('parameter', models.ForeignKey(to='core.Parameter')),
                ('round_configuration', models.ForeignKey(
                    related_name=b'parameter_value_set', to='core.RoundConfiguration')),
            ],
            options={
                'ordering': ['round_configuration', 'parameter', 'date_created'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SpoolParticipantStatistics',
            fields=[
                ('id', models.AutoField(
                    verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('absences', models.PositiveIntegerField(default=0)),
                ('discharges', models.PositiveIntegerField(default=0)),
                ('participations', models.PositiveIntegerField(default=0)),
                ('invitations', models.PositiveIntegerField(default=0)),
                ('participant', models.ForeignKey(
                    related_name=b'spool_statistics_set', to='core.Participant')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='rounddata',
            unique_together=set(
                [('round_configuration', 'repeating_round_sequence_number', 'experiment')]),
        ),
        migrations.AddField(
            model_name='participantrounddatavalue',
            name='parameter',
            field=models.ForeignKey(to='core.Parameter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participantrounddatavalue',
            name='participant_group_relationship',
            field=models.ForeignKey(
                related_name=b'data_value_set', to='core.ParticipantGroupRelationship'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participantrounddatavalue',
            name='round_data',
            field=models.ForeignKey(
                related_name=b'participant_data_value_set', to='core.RoundData'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participantrounddatavalue',
            name='target_data_value',
            field=models.ForeignKey(
                related_name=b'target_data_value_set', blank=True, to='core.ParticipantRoundDataValue', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participantgrouprelationship',
            name='round_joined',
            field=models.ForeignKey(to='core.RoundConfiguration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participant',
            name='experiments',
            field=models.ManyToManyField(
                related_name=b'participant_set', through='core.ParticipantExperimentRelationship', to='core.Experiment'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participant',
            name='groups',
            field=models.ManyToManyField(
                related_name=b'participant_set', through='core.ParticipantGroupRelationship', to='core.Group'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participant',
            name='institution',
            field=models.ForeignKey(
                blank=True, to='core.Institution', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='participant',
            name='user',
            field=models.OneToOneField(
                related_name=b'participant', verbose_name='Django User', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invitation',
            name='participant',
            field=models.ForeignKey(to='core.Participant'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invitation',
            name='sender',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='grouprounddatavalue',
            name='parameter',
            field=models.ForeignKey(to='core.Parameter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='grouprounddatavalue',
            name='round_data',
            field=models.ForeignKey(
                related_name=b'group_data_value_set', to='core.RoundData'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='groupclusterdatavalue',
            name='parameter',
            field=models.ForeignKey(to='core.Parameter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='groupclusterdatavalue',
            name='round_data',
            field=models.ForeignKey(
                related_name=b'group_cluster_data_value_set', to='core.RoundData'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='groupactivitylog',
            name='round_configuration',
            field=models.ForeignKey(to='core.RoundConfiguration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimentparametervalue',
            name='parameter',
            field=models.ForeignKey(to='core.Parameter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimentmetadata',
            name='parameters',
            field=models.ManyToManyField(to='core.Parameter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimenter',
            name='institution',
            field=models.ForeignKey(
                blank=True, to='core.Institution', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimenter',
            name='user',
            field=models.OneToOneField(
                related_name=b'experimenter', verbose_name='Django User', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimentconfiguration',
            name='creator',
            field=models.ForeignKey(
                related_name=b'experiment_configuration_set', to='core.Experimenter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimentconfiguration',
            name='experiment_metadata',
            field=models.ForeignKey(
                related_name=b'experiment_configuration_set', to='core.ExperimentMetadata'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experimentactivitylog',
            name='round_configuration',
            field=models.ForeignKey(to='core.RoundConfiguration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experiment',
            name='experiment_configuration',
            field=models.ForeignKey(to='core.ExperimentConfiguration'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experiment',
            name='experiment_metadata',
            field=models.ForeignKey(to='core.ExperimentMetadata'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='experiment',
            name='experimenter',
            field=models.ForeignKey(to='core.Experimenter'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='target_participant',
            field=models.ForeignKey(related_name=b'target_participant_chat_message_set',
                                    blank=True, to='core.ParticipantGroupRelationship', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookmarkedexperimentmetadata',
            name='experiment_metadata',
            field=models.ForeignKey(
                related_name=b'bookmarked_experiment_metadata_set', to='core.ExperimentMetadata'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='bookmarkedexperimentmetadata',
            name='experimenter',
            field=models.ForeignKey(
                related_name=b'bookmarked_experiment_metadata_set', to='core.Experimenter'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='bookmarkedexperimentmetadata',
            unique_together=set([('experimenter', 'experiment_metadata')]),
        ),
    ]
