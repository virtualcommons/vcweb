import json
import logging
from datetime import date, timedelta

from django.conf import settings
from django.core.cache import cache

from vcweb.core.models import ParticipantRoundDataValue, ChatMessage, Like, Comment
from vcweb.core.tests import BaseVcwebTest
from .models import (Activity, get_lighterprints_experiment_metadata, get_activity_performed_parameter,
                     get_footprint_level, get_treatment_type_parameter, get_leaderboard_parameter,
                     get_linear_public_good_parameter, is_scheduled_activity_experiment, is_level_based_experiment,
                     is_high_school_treatment, is_community_treatment, get_available_activity_parameter)
from .services import (GroupScores, get_individual_points, GroupActivity, CommunityEmailGenerator)
from .views import (LighterprintsViewModel, LevelBasedViewModel, CommunityViewModel, HighSchoolViewModel)

logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):
    scheduled_activity_names = ('eat-local-lunch', 'enable-sleep-on-computer', 'share-your-ride', 'recycle-paper',
                                'air-dry-clothes', 'bike-or-walk', 'eat-green-lunch', 'computer-off-night',
                                'cold-water-wash')

    def setUp(self, treatment_type='LEVEL_BASED', leaderboard=True, linear_public_good=True, **kwargs):
        super(BaseTest, self).setUp(experiment_metadata=get_lighterprints_experiment_metadata(), number_of_rounds=3,
                                    **kwargs)
        cache.clear()
        e = self.experiment
        e.start_date = date.today()
        e.save()
        ec = self.experiment_configuration
        ec.has_daily_rounds = True
        ec.set_parameter_value(parameter=get_leaderboard_parameter(), boolean_value=leaderboard)
        ec.set_parameter_value(parameter=get_linear_public_good_parameter(), boolean_value=linear_public_good)
        ec.set_parameter_value(parameter=get_treatment_type_parameter(), string_value=treatment_type)
        ec.round_configuration_set.update(initialize_data_values=True)
        ec.payment_information = '''unique text for payment information: tobacco hornworm'''
        ec.save()

    @property
    def scheduled_activity_ids(self):
        return Activity.objects.filter(name__in=BaseTest.scheduled_activity_names).values_list('pk', flat=True)

    def default_activities(self):
        return Activity.objects.all()

    def create_scheduled_activities(self):
        ec = self.experiment_configuration
        for rc in ec.round_configuration_set.all():
            for activity_pk in self.scheduled_activity_ids:
                rc.parameter_value_set.create(parameter=get_available_activity_parameter(),
                                              int_value=activity_pk)

    def perform_activities(self, activities=None, force=False, round_data=None):
        e = self.experiment
        if round_data is None:
            round_data = e.current_round_data
        if activities is None:
            activities = self.default_activities()
        performed_activities = set()
        for pgr in e.participant_group_relationships:
            participant = pgr.participant
            self.assertTrue(self.login_participant(participant),
                            "%s failed to login" % participant)
            for activity in activities:
                expected_success = Activity.objects.is_activity_available(activity, pgr, round_data)
                if expected_success:
                    performed_activities.add(activity)
                response = self.post(self.reverse('lighterprints:perform_activity'), {
                    'participant_group_id': pgr.id,
                    'activity_id': activity.pk
                }, follow=True)
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
                if force and not expected_success:
                    ParticipantRoundDataValue.objects.create(
                        parameter=get_activity_performed_parameter(),
                        participant_group_relationship=pgr,
                        round_data=round_data,
                        int_value=activity.pk
                    )

        return performed_activities

    class Meta:
        abstract = True


class LevelBasedTest(BaseTest):

    """
    FIXME: only works on level based experiments without has_daily_rounds, fix to operate on scheduled activity rounds
    as well by adding available_activity parameters and scheduled activities
    """

    def setUp(self, **kwargs):
        super(LevelBasedTest, self).setUp(treatment_type='LEVEL_BASED', **kwargs)

    def default_activities(self):
        return Activity.objects.at_level(1)


class ScheduledActivityTest(BaseTest):

    def default_activities(self):
        return list(Activity.objects.scheduled(self.experiment.current_round))


class CommunityTreatmentTest(ScheduledActivityTest):

    def setUp(self, **kwargs):
        super(CommunityTreatmentTest, self).setUp(treatment_type='COMMUNITY', **kwargs)
        rc = self.experiment.current_round
        rc.create_group_clusters = True
        rc.save()
        self.create_scheduled_activities()

    def test_treatment_type(self):
        e = self.experiment
        e.activate()
        self.assertFalse(is_level_based_experiment(e))
        self.assertTrue(is_scheduled_activity_experiment(e))
        self.assertFalse(is_high_school_treatment(e))
        self.assertTrue(is_community_treatment(e))
        today = date.today()
        self.assertEqual(e.start_date, today)
        self.assertEqual(e.end_date, today + timedelta(e.number_of_rounds))

    def test_perform_available_activities(self):
        e = self.experiment
        e.activate()
        exchange_rate = e.experiment_configuration.exchange_rate
        while e.has_next_round:
            gs = GroupScores(e)
            for group in e.groups:
                self.assertEqual(0, gs.average_daily_points(group))
                self.assertEqual(0, gs.average_daily_cluster_points(group=group))
                self.assertEqual(0, gs.total_daily_points(group))
                self.assertEqual(0, gs.daily_earnings(group))
            performed_activities = self.perform_activities(round_data=e.current_round_data)
            total_expected_points = sum([a.points for a in performed_activities])
            gs = GroupScores(e)
            for group in e.groups:
                self.assertEqual(total_expected_points, gs.average_daily_points(group))
                self.assertEqual(total_expected_points, gs.average_daily_cluster_points(group=group))
                self.assertEqual(total_expected_points * group.size, gs.total_daily_points(group))
                self.assertEqual(total_expected_points * e.current_round_sequence_number,
                                 gs.total_average_points(group))
                self.assertAlmostEqual(total_expected_points * exchange_rate, gs.daily_earnings(group))
                self.assertAlmostEqual(total_expected_points * exchange_rate * e.current_round_sequence_number,
                                       gs.total_earnings(group))
            e.advance_to_next_round()

    def test_perform_all_activities(self):
        e = self.experiment
        e.activate()
        exchange_rate = e.experiment_configuration.exchange_rate
        self.assertEqual(exchange_rate, 0.02)
        expected_points = 250
        while e.has_next_round:
            gs = GroupScores(e)
            total_group_score = expected_points * (e.current_round_sequence_number - 1)
            for group in e.groups:
                self.assertEqual(0, gs.average_daily_points(group))
                self.assertEqual(0, gs.average_daily_cluster_points(group=group))
                self.assertEqual(0, gs.total_daily_points(group))
                self.assertEqual(total_group_score,
                                 gs.total_average_points(group))
                self.assertEqual(0, gs.daily_earnings(group))
                self.assertAlmostEqual(total_group_score * exchange_rate, gs.total_earnings(group))
            self.perform_activities(force=True, round_data=e.current_round_data)
            gs = GroupScores(e)
            for group in e.groups:
                self.assertEqual(expected_points, gs.average_daily_points(group))
                self.assertEqual(expected_points, gs.average_daily_cluster_points(group=group))
                self.assertEqual(expected_points * group.size, gs.total_daily_points(group))
                self.assertEqual(expected_points * e.current_round_sequence_number, gs.total_average_points(group))
                self.assertAlmostEqual(expected_points * exchange_rate, gs.daily_earnings(group))
                self.assertAlmostEqual(expected_points * e.current_round_sequence_number * exchange_rate,
                                       gs.total_earnings(group))
            e.advance_to_next_round()

    def test_summary_emails(self):
        e = self.experiment
        e.activate()
        current_round = e.current_round
        activities = list(Activity.objects.scheduled(current_round))
        self.assertEqual(250, sum(Activity.objects.scheduled(current_round).values_list('points', flat=True)))
        current_round_data = e.current_round_data
        # perform activities
        for pgr in e.participant_group_relationships:
            ChatMessage.objects.create(participant_group_relationship=pgr,
                                       string_value='Harrowing message from %s' % pgr)
            for a in activities:
                ParticipantRoundDataValue.objects.create(
                    parameter=get_activity_performed_parameter(),
                    participant_group_relationship=pgr,
                    round_data=current_round_data,
                    int_value=a.pk
                )
        gs = GroupScores(e)
        for group in e.groups:
            summary_emails = gs.email_generator.generate(group)
            group_emails = [pgr.participant.email for pgr in group.participant_group_relationship_set.all()]
            for email in summary_emails:
                for recipient in email.recipients():
                    if recipient != settings.DEFAULT_FROM_EMAIL:
                        group_emails.remove(recipient)
                self.assertTrue(email.recipients())
                self.assertTrue("5 chat messages were posted" in email.body)
                self.assertTrue("You earned 250 point(s)." in email.body)
                self.assertTrue("Members of your group earned, on average, 250.0 point(s)." in email.body)
                self.assertTrue("Members of all groups earned, on average, 250.0 point(s)." in email.body)
            self.assertFalse(group_emails, "Group emails should have all been removed")

    def test_payment_information(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            e.advance_to_next_round()
        gs = GroupScores(e)
        for group in e.groups:
            summary_emails = gs.email_generator.generate(group)
            for email in summary_emails:
                self.assertTrue(email.recipients())
                self.assertTrue("tobacco hornworm" in email.body)

    def test_view_model(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            lvm = LighterprintsViewModel.create(pgr)
            self.assertEqual(lvm.template_name, CommunityViewModel.template_name)
            self.assertEqual(type(lvm.email_generator), CommunityEmailGenerator)
            self.assertIsNotNone(lvm.group_cluster)
            self.assertIsNotNone(lvm.group_data)
            lvm_dict = lvm.to_dict()
            self.assertTrue('averageClusterPoints' in lvm_dict)


class HighSchoolTreatmentTest(BaseTest):

    def setUp(self, **kwargs):
        super(HighSchoolTreatmentTest, self).setUp(treatment_type='HIGH_SCHOOL', **kwargs)

    def test_treatment_type(self):
        e = self.experiment
        e.activate()
        self.assertFalse(is_level_based_experiment(e))
        self.assertTrue(is_scheduled_activity_experiment(e))
        self.assertTrue(is_high_school_treatment(e))
        self.assertFalse(is_community_treatment(e))

    def test_view_model(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            lvm = LighterprintsViewModel.create(pgr)
            self.assertEqual(lvm.template_name, HighSchoolViewModel.template_name)
            self.assertEqual(type(lvm), HighSchoolViewModel)


class LevelTreatmentTest(LevelBasedTest):

    def test_treatment_type(self):
        e = self.experiment
        self.assertTrue(is_level_based_experiment(e))
        self.assertFalse(is_scheduled_activity_experiment(e))
        self.assertFalse(is_high_school_treatment(e))
        self.assertFalse(is_community_treatment(e))

    def test_view_model(self):
        e = self.experiment
        for pgr in e.participant_group_relationships:
            lvm = LighterprintsViewModel.create(pgr)
            self.assertEqual(lvm.template_name, LevelBasedViewModel.template_name)

    def test_participate(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            self.assertTrue(self.login_participant(pgr.participant))
            response = self.get(e.participant_url, follow=True)
            self.assertEqual(response.status_code, 200)

    def test_footprint_level_initialized(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            rd = e.current_round_data
            for g in e.groups:
                self.assertEqual(1, get_footprint_level(g, round_data=rd))
            e.advance_to_next_round()


class ActivityViewTest(BaseTest):

    def test_list(self):
        for pgr in self.experiment.participant_group_relationships:
            participant = pgr.participant
            response = self.client.get('/lighterprints/activity/list', {'format': 'json'})
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
        level_one_activities = Activity.objects.filter(level=1).values_list('pk', flat=True)
        for pgr in e.participant_group_relationships:
            for activity_pk in level_one_activities:
                activity_performed = ParticipantRoundDataValue.objects.create(
                    participant_group_relationship=pgr,
                    round_data=current_round_data,
                    parameter=get_activity_performed_parameter()
                )
                activity_performed.update_int(activity_pk)
        gs = e.groups
        group_scores = GroupScores(e, round_data=current_round_data, groups=gs)
        logger.debug("group scores created for current round data")
        for group in gs:
            self.assertEqual(get_footprint_level(group), 1, 'All participants should still be on level 1')
            self.assertEqual(group_scores.average_daily_points(group), 177)
        # manually invoking daily_update
        e.advance_to_next_round()
        group_scores = GroupScores(e, round_data=current_round_data, groups=gs)
        for group in gs:
            self.assertEqual(get_footprint_level(group), 2, 'All levels should have advanced to 2')
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
            group_activity = GroupActivity(pgr)
            self.assertEqual(len(group_activity.all_activities), len(performed_activities) * pgr.group.size)

    def test_group_activity_email(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        group_scores = GroupScores(e)
        messages = list(group_scores.generate_daily_update_messages())
        self.assertEqual(len(messages), len(e.groups) * e.experiment_configuration.max_group_size)


class PerformActivityTest(BaseTest):

    def test_perform_multiple_activities(self):
        e = self.experiment
        e.activate()
        # gets all activities with no params
        performed_activities = self.perform_activities()
        for pgr in e.participant_group_relationships:
            participant = pgr.participant
            self.login_participant(participant)
            for activity in performed_activities:
                # trying to do the same activity again should result in an
                # error response
                response = self.post(self.reverse('lighterprints:perform_activity'), {
                    'participant_group_id': pgr.id,
                    'activity_id': activity.pk
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertFalse(json_object['success'])

    def test_comments_likes(self):
        e = self.experiment
        e.activate()
        self.perform_activities()
        activity_performed_parameter = get_activity_performed_parameter()
        for pgr in e.participant_group_relationships:
            performed_activity_ids = ParticipantRoundDataValue.objects.filter(
                participant_group_relationship=pgr,
                parameter=activity_performed_parameter).values_list('pk', flat=True)
            participant = pgr.participant
            self.login_participant(participant)
            # test comments on performed activities
            text = "This is a harrowing comment by %s" % pgr
            self.assertFalse(Like.objects.filter(participant_group_relationship=pgr).exists())
            self.assertFalse(Comment.objects.filter(participant_group_relationship=pgr).exists())
            for performed_activity_id in performed_activity_ids:
                # test comment posting on performed activities
                response = self.post('lighterprints:post_comment', {
                    'participant_group_id': pgr.pk,
                    'message': text,
                    'target_id': performed_activity_id
                })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertTrue(json_object['success'])
                c = Comment.objects.get(participant_group_relationship__pk=pgr.pk,
                                        target_data_value__id=performed_activity_id)
                self.assertEqual(c.string_value, text)
                # test likes on comment and performed activities
                response = self.post('lighterprints:like', {
                    'participant_group_id': pgr.pk,
                    'target_id': c.pk
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.content)['success'])
                self.assertTrue(Like.objects.filter(participant_group_relationship=pgr,
                                                    target_data_value__id=c.pk).exists())

                response = self.post('lighterprints:like', {
                    'participant_group_id': pgr.pk,
                    'target_id': performed_activity_id
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(json.loads(response.content)['success'])
                self.assertTrue(Like.objects.filter(participant_group_relationship=pgr,
                                                    target_data_value__id=performed_activity_id).exists())


class LevelBasedGroupScoreTest(LevelBasedTest):

    def test(self):
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


class TestRoundEndedSignal(BaseTest):

    def test_system_daily_tick(self):
        self.experiment.activate()
        self.assertEqual(self.experiment.current_round.sequence_number, 1)
        from vcweb.core.cron import system_daily_tick
        system_daily_tick()
        self.assertEqual(self.reload_experiment().current_round.sequence_number, 2)


class ChatMessageTest(BaseTest):

    def test_post_chat(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            message = "Chat message from %s" % pgr
            self.login_participant(pgr.participant)
            response = self.post('lighterprints:post_chat',
                                 {'participant_group_id': pgr.pk, 'message': message})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(json.loads(response.content)['success'])
            self.assertEqual(ChatMessage.objects.get(participant_group_relationship=pgr).string_value, message)


class LikeTest(BaseTest):

    def test(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            message = "Chat message from %s" % pgr
            self.assertTrue(self.login_participant(pgr.participant))
            response = self.post('lighterprints:post_chat',
                                 {'participant_group_id': pgr.pk, 'message': message})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(json.loads(response.content)['success'])
            self.assertEqual(ChatMessage.objects.get(participant_group_relationship=pgr).string_value, message)
        for pgr in e.participant_group_relationships:
            for cm in ChatMessage.objects.for_group(pgr.group):
                if cm.participant_group_relationship != pgr:
                    self.assertTrue(self.login_participant(pgr.participant))
                    response = self.post(
                        'lighterprints:like',
                        {'participant_group_id': pgr.pk, 'target_id': cm.pk}
                    )
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(json.loads(response.content)['success'])
                    self.assertTrue(Like.objects.filter(participant_group_relationship__pk=pgr.pk,
                                                        target_data_value__pk=cm.pk).exists())
