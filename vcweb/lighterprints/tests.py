from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import ParticipantGroupRelationship
from vcweb.lighterprints.views import *
from vcweb.lighterprints.models import *


import logging
import json

logger = logging.getLogger(__name__)

class BaseTest(BaseVcwebTest):
    fixtures = [ 'lighterprints_experiment_metadata', 'activities' ]

    def perform_activities(self, activities=None):
        rd = self.experiment.current_round_data
        activities = Activity.objects.at_level(1)
        performed_activities = set()
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=self.experiment):
            participant = participant_group_relationship.participant
            self.assertTrue(self.client.login(username=participant.email, password='test'), "%s failed to login" % participant)
            for activity in activities:
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                expected_success = activity.is_available_for(participant_group_relationship, rd)
                logger.debug("expected success: %s", expected_success)
                if expected_success:
                    performed_activities.add(activity)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                    }, follow=True)
                logger.debug("response: %s - request chain %s", response, response.redirect_chain)
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
        return performed_activities

    def setUp(self, **kwargs):
        super(BaseTest, self).setUp(experiment_metadata=get_lighterprints_experiment_metadata(), **kwargs)
        logger.debug("loaded experiment %s", self.experiment)

class ActivityViewTest(BaseTest):
    def test_list(self):
        for pgr in self.experiment.participant_group_relationships:
            participant = pgr.participant
            response = self.client.get('/lighterprints/activity/list', {'format':'json'})
            self.assertEqual(response.status_code, 403)
            self.client.login(username=participant.email, password='test')
            response = self.client.get('/lighterprints/activity/list', {'format':'json', 'participant_group_id': pgr.id})
            self.assertEqual(response.status_code, 200)
            self.client.logout()
            response = self.client.get('/lighterprints/activity/list', {'format':'json', 'participant_group_id': pgr.id})
            self.assertEqual(response.status_code, 403)


class UpdateLevelTest(BaseTest):
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
        update_active_experiments(self, start_date=date.today())
        gs = e.groups
        group_scores = GroupScores(e, current_round_data, gs)
        for group in gs:
            logger.debug("all levels should be 2 now")
            self.assertEqual(get_footprint_level(group), 2)
            self.assertEqual(group_scores.average_points(group), 177)


class GroupActivityTest(BaseTest):
    def test_group_activity(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        for pgr in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            (group_activity, chat_messages) = get_group_activity(pgr)
            logger.debug("group activity is %s", len(group_activity))
            self.assertEqual(len(group_activity), len(performed_activities) * pgr.group.size)

    def test_group_activity_email(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        group_scores = GroupScores(e, e.current_round_data)
        for group in e.groups:
            messages = group_scores.create_level_based_group_summary_emails(group, level=2)
            self.assertEquals(len(messages), group.size)


class ActivityTest(BaseTest):

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
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                expected_success = activity.is_available_for(participant_group_relationship, rd)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
# trying to do the same activity again should result in an error response
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                    })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertFalse(json_object['success'])

            performed_activity_ids = get_performed_activity_ids(participant_group_relationship)
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
                self.assertIsNotNone(json_object['viewModel']);


class GroupScoreTest(ActivityTest):
    def test_individual_points(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        logger.debug("performed activities: %s", performed_activities)
        for pgr in e.participant_group_relationships:
            self.assertEqual(get_individual_points(pgr), 0)
            self.assertTrue(get_individual_points(pgr, end_date=date.today() + timedelta(1)) > 0)

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
            self.assertEqual(group_scores.average_points(group), expected_avg_points_per_person)
            self.assertEqual(group_scores.total_points(group), expected_avg_points_per_person * group.size)
