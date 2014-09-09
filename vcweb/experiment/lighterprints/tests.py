import json
import logging
from datetime import date, timedelta

from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import ParticipantRoundDataValue
from .models import (Activity, get_lighterprints_experiment_metadata, get_activity_performed_parameter,
                     get_footprint_level, get_performed_activity_ids, get_treatment_type_parameter,
                     is_scheduled_activity_experiment, get_treatment_type)
from .services import (GroupScores, get_individual_points, send_summary_emails, get_group_activity)


logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):
    """
    FIXME: only works on level based experiments without has_daily_rounds, fix to operate on scheduled activity rounds
    as well by adding available_activity parameters and scheduled activities
    """

    def perform_activities(self, activities=None):
        rd = self.experiment.current_round_data
        activities = Activity.objects.at_level(1)
        performed_activities = set()
        for participant_group_relationship in self.experiment.participant_group_relationships:
            participant = participant_group_relationship.participant
            self.assertTrue(self.client.login(username=participant.email, password='test'),
                            "%s failed to login" % participant)
            for activity in activities:
                expected_success = activity.is_available_for(participant_group_relationship, rd)
                if expected_success:
                    performed_activities.add(activity)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                }, follow=True)
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
        return performed_activities

    def setUp(self, treatment_type='LEADERBOARD', **kwargs):
        super(BaseTest, self).setUp(experiment_metadata=get_lighterprints_experiment_metadata(), **kwargs)
        ec = self.experiment_configuration
        ec.has_daily_rounds = True
        ec.save()
        for rc in self.round_configurations.all():
            rc.set_parameter_value(parameter=get_treatment_type_parameter(), string_value=treatment_type)
            rc.initialize_data_values = True
            rc.save()

    class Meta:
        abstract = True


class LevelBasedTest(BaseTest):

    def setUp(self, **kwargs):
        super(LevelBasedTest, self).setUp(treatment_type='LEVEL_BASED', **kwargs)


class LevelTreatmentTest(LevelBasedTest):

    def test_treatment_type(self):
        for rc in self.round_configurations.all():
            self.assertFalse(is_scheduled_activity_experiment(rc))
            self.assertEqual('LEVEL_BASED', get_treatment_type(rc).string_value)

    def test_footprint_level_initialized(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            rd = e.current_round_data
            for g in e.groups:
                self.assertEqual(1, get_footprint_level(g, round_data=rd))
            e.advance_to_next_round()


class ActivityViewTest(LevelBasedTest):

    def test_list(self):
        for pgr in self.experiment.participant_group_relationships:
            participant = pgr.participant
            response = self.client.get(
                '/lighterprints/activity/list', {'format': 'json'})
            self.assertEqual(response.status_code, 403)
            self.client.login(username=participant.email, password='test')
            response = self.client.get('/lighterprints/activity/list',
                                       {'format': 'json', 'participant_group_id': pgr.id})
            self.assertEqual(response.status_code, 200)
            self.client.logout()
            response = self.client.get('/lighterprints/activity/list',
                                       {'format': 'json', 'participant_group_id': pgr.id})
            self.assertEqual(response.status_code, 403)


class UpdateLevelTest(LevelBasedTest):

    def test_daily_points(self):
        e = self.experiment
        e.activate()
        current_round_data = e.current_round_data
        # initialize participant carbon savings
        level_one_activities = Activity.objects.filter(level=1)
        for pgr in e.participant_group_relationships:
            for activity in level_one_activities:
                activity_performed = ParticipantRoundDataValue.objects.create(
                    participant_group_relationship=pgr,
                    round_data=current_round_data,
                    parameter=get_activity_performed_parameter()
                )
                activity_performed.int_value = activity.pk
                activity_performed.save()
        send_summary_emails(e, start_date=date.today())
        gs = e.groups
        group_scores = GroupScores(e, current_round_data, gs)
        for group in gs:
            self.assertEqual(get_footprint_level(group), 2, 'All levels should have advanced to 2')
            self.assertEqual(group_scores.average_daily_points(group), 177)


class GroupActivityTest(LevelBasedTest):

    def test_group_activity(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        for pgr in e.participant_group_relationships:
            (group_activity, chat_messages) = get_group_activity(pgr)
            self.assertEqual(len(group_activity), len(performed_activities) * pgr.group.size)

    def test_group_activity_email(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        group_scores = GroupScores(e, e.current_round_data)
        for group in e.groups:
            messages = group_scores.create_level_based_group_summary_emails(group, level=2)
            self.assertEqual(len(messages), group.size)


class ActivityTest(LevelBasedTest):

    def test_view(self):
        logger.debug("testing do activity view")
        e = self.experiment
        e.activate()
        # gets all activities with no params
        activities = Activity.objects.all()
        rd = e.current_round_data
        for participant_group_relationship in e.participant_group_relationships:
            logger.debug("all available activities: %s", activities)
            participant = participant_group_relationship.participant
            self.client.login(username=participant.email, password='test')
            for activity in activities:
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant,
                             activity)
                expected_success = activity.is_available_for(participant_group_relationship, rd)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
                # trying to do the same activity again should result in an
                # error response
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertFalse(json_object['success'])

            performed_activity_ids = get_performed_activity_ids(
                participant_group_relationship)
            text = "This is a harrowing comment"
            for activity_id in performed_activity_ids:
                logger.debug("posting comment on id %s", activity_id)
                response = self.client.post('/lighterprints/api/comment', {
                    'participant_group_id': participant_group_relationship.pk,
                    'message': text,
                    'target_id': activity_id
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertTrue(json_object)
                self.assertIsNotNone(json_object['viewModel'])


class GroupScoreTest(ActivityTest):

    def test_individual_points(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        for pgr in e.participant_group_relationships:
            self.assertEqual(get_individual_points(pgr), 0,
                             'get_individual_points with no args looks for previous day activities, should be 0')
            self.assertTrue(get_individual_points(pgr, end_date=date.today() + timedelta(1)) > 0,
                            'get_individual_points with explicit end date should be > 0')

    def test_group_score(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        gs = e.groups
        group_scores = GroupScores(e, groups=gs)
        # expected average points per person is the straight sum of all activities in the performed activities because
        # every participant in the group has performed them
        expected_avg_points_per_person = sum([activity.points for activity in performed_activities])
        for group in gs:
            self.assertEqual(group_scores.average_daily_points(group), expected_avg_points_per_person)
            self.assertEqual(group_scores.total_daily_points(group), expected_avg_points_per_person * group.size)
