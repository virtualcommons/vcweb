import json
import logging

from django.core.cache import cache
from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import ParticipantRoundDataValue, ChatMessage, Like, Comment
from .models import (Activity, get_lighterprints_experiment_metadata, get_activity_performed_parameter,
                     get_footprint_level, get_performed_activity_ids, get_treatment_type_parameter,
                     is_scheduled_activity_experiment, is_level_based_experiment, is_high_school_treatment)
from .services import (GroupScores, get_individual_points, get_group_activity)


logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):

    def setUp(self, treatment_type='LEADERBOARD', **kwargs):
        super(BaseTest, self).setUp(
            experiment_metadata=get_lighterprints_experiment_metadata(), **kwargs)
        cache.clear()
        ec = self.experiment_configuration
        ec.has_daily_rounds = True
        ec.set_parameter_value(
            parameter=get_treatment_type_parameter(), string_value=treatment_type)
        ec.save()
        ec.round_configuration_set.all().update(initialize_data_values=True)

    class Meta:
        abstract = True


class LevelBasedTest(BaseTest):

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
                expected_success = activity.is_available_for(
                    participant_group_relationship, rd)
                if expected_success:
                    performed_activities.add(activity)
                response = self.post(self.reverse('lighterprints:perform_activity'), {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                }, follow=True)
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
        return performed_activities

    def setUp(self, **kwargs):
        super(LevelBasedTest, self).setUp(
            treatment_type='LEVEL_BASED', **kwargs)


class LevelTreatmentTest(LevelBasedTest):

    def test_treatment_type(self):
        self.assertTrue(is_level_based_experiment(self.experiment))
        self.assertFalse(is_scheduled_activity_experiment(self.experiment))
        self.assertFalse(is_high_school_treatment(self.experiment))

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
        self.assertTrue(is_level_based_experiment(e))
        # initialize participant carbon savings
        level_one_activities = Activity.objects.filter(
            level=1).values_list('pk', flat=True)
        for pgr in e.participant_group_relationships:
            for activity_pk in level_one_activities:
                activity_performed = ParticipantRoundDataValue.objects.create(
                    participant_group_relationship=pgr,
                    round_data=current_round_data,
                    parameter=get_activity_performed_parameter()
                )
                activity_performed.update_int(activity_pk)
        gs = e.groups
        group_scores = GroupScores(e, current_round_data, gs)
        logger.debug("group scores created for current round data")
        for group in gs:
            self.assertEqual(
                get_footprint_level(group), 1, 'All participants should still be on level 1')
            self.assertEqual(group_scores.average_daily_points(group), 177)
        # manually invoking daily_update
        e.advance_to_next_round()
        group_scores = GroupScores(e, current_round_data, gs)
        for group in gs:
            self.assertEqual(
                get_footprint_level(group), 2, 'All levels should have advanced to 2')
            self.assertEqual(group_scores.average_daily_points(group), 177)
        group_scores = GroupScores(e, groups=gs)
        for group in gs:
            self.assertEqual(
                get_footprint_level(group), 2, 'Footprint level should still be 2')
            self.assertEqual(0, group_scores.average_daily_points(group),
                             'average daily points should have been reset to 0')


class GroupActivityTest(LevelBasedTest):

    def test_group_activity(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        for pgr in e.participant_group_relationships:
            (group_activity, chat_messages) = get_group_activity(pgr)
            self.assertEqual(
                len(group_activity), len(performed_activities) * pgr.group.size)

    def test_group_activity_email(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        group_scores = GroupScores(e, e.current_round_data)
        for group in e.groups:
            messages = group_scores.create_level_based_group_summary_emails(
                group, level=2)
            self.assertEqual(len(messages), group.size)


class PerformActivityTest(LevelBasedTest):

    def test_comments_likes(self):
        logger.debug("testing do activity view")
        e = self.experiment
        e.activate()
        # gets all activities with no params
        activities = Activity.objects.all()
        rd = e.current_round_data
        for participant_group_relationship in e.participant_group_relationships:
            logger.debug("all available activities: %s", activities)
            participant = participant_group_relationship.participant
            self.login_participant(participant, password='test')
            for activity in activities:
                logger.debug("participant %s performing activity %s", participant, activity)
                expected_success = activity.is_available_for(participant_group_relationship, rd)
                response = self.post('lighterprints:perform_activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
                # trying to do the same activity again should result in an
                # error response
                response = self.post(self.reverse('lighterprints:perform_activity'), {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertFalse(json_object['success'])

            # test comments on performed activities
            performed_activity_ids = get_performed_activity_ids(participant_group_relationship)
            text = "This is a harrowing comment by %s" % participant_group_relationship
            self.assertFalse(Like.objects.filter(
                participant_group_relationship=participant_group_relationship).exists())
            self.assertFalse(Comment.objects.filter(
                participant_group_relationship=participant_group_relationship).exists())
            for performed_activity_id in performed_activity_ids:
                # test comment posting on performed activities
                response = self.post('lighterprints:post_comment', {
                    'participant_group_id': participant_group_relationship.pk,
                    'message': text,
                    'target_id': performed_activity_id
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertTrue(json_object['success'])
                c = Comment.objects.get(participant_group_relationship__pk=participant_group_relationship.pk,
                                        target_data_value__id=performed_activity_id)
                self.assertEqual(c.string_value, text)
                # test likes on comment and performed activities
                response = self.post('lighterprints:like', {
                    'participant_group_id': participant_group_relationship.pk,
                    'target_id': c.pk
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.content)['success'])
                self.assertTrue(Like.objects.filter(participant_group_relationship=participant_group_relationship,
                                                    target_data_value__id=c.pk).exists())

                response = self.post('lighterprints:like', {
                    'participant_group_id': participant_group_relationship.pk,
                    'target_id': performed_activity_id
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.content)['success'])
                self.assertTrue(Like.objects.filter(participant_group_relationship=participant_group_relationship,
                                                    target_data_value__id=performed_activity_id).exists())


class GroupScoreTest(LevelBasedTest):

    def test_group_score(self):
        e = self.experiment
        e.activate()
        performed_activities = self.perform_activities()
        # expected average points per person is the straight sum of all activities in the performed activities because
        # every participant in the group has performed them
        expected_avg_points_per_person = sum([activity.points for activity in performed_activities])
        gs = e.groups
        group_scores = GroupScores(e, groups=gs)
        for group in gs:
            self.assertEqual(group_scores.average_daily_points(group), expected_avg_points_per_person)
            self.assertEqual(group_scores.total_daily_points(group), expected_avg_points_per_person * group.size)
            for pgr in group.participant_group_relationship_set.all():
                self.assertEqual(get_individual_points(
                    pgr, group_scores.round_data), expected_avg_points_per_person)
        e.advance_to_next_round()
        group_scores = GroupScores(e, groups=gs)
        for group in gs:
            self.assertEqual(group_scores.average_daily_points(group), 0)
            self.assertEqual(group_scores.total_daily_points(group), 0)


class TestRoundEndedSignal(LevelBasedTest):

    def test_system_daily_tick(self):
        self.experiment.activate()
        self.assertEqual(self.experiment.current_round.sequence_number, 1)
        from vcweb.core.cron import system_daily_tick
        system_daily_tick()
        self.assertEqual(self.reload_experiment().current_round.sequence_number, 2)


class ChatMessageTest(LevelBasedTest):

    def test_chat_and_likes(self):
        self.experiment.activate()
        for pgr in self.experiment.participant_group_relationships:
            message = "Chat message from %s" % pgr
            self.login_participant(pgr.participant)
            response = self.post('lighterprints:post_chat',
                                 {'participant_group_id': pgr.pk, 'message': message})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(json.loads(response.content)['success'])
            self.assertEqual(ChatMessage.objects.get(participant_group_relationship=pgr).string_value, message)


class LikeTest(LevelBasedTest):

    def test(self):
        self.experiment.activate()
        for pgr in self.experiment.participant_group_relationships:
            message = "Chat message from %s" % pgr
            self.login_participant(pgr.participant)
            response = self.post('lighterprints:post_chat',
                                 {'participant_group_id': pgr.pk, 'message': message})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(json.loads(response.content)['success'])
            self.assertEqual(ChatMessage.objects.get(participant_group_relationship=pgr).string_value, message)
