from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import ParticipantGroupRelationship
from vcweb.lighterprints.views import *
from vcweb.lighterprints.models import *

from lxml import etree

import logging
import simplejson as json
import os

logger = logging.getLogger(__name__)

class BaseTest(BaseVcwebTest):
    fixtures = [ 'activities' ]
    def setUp(self, **kwargs):
        super(BaseTest, self).setUp()
        experiment_metadata = get_lighterprints_experiment_metadata()
        self.load_experiment(experiment_metadata=experiment_metadata, **kwargs)

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
        e.start_round()
        current_round_data = e.current_round_data
# initialize participant carbon savings
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            for activity in Activity.objects.filter(level=1):
                activity_performed = participant_group_relationship.participant_data_value_set.create(round_data=current_round_data, parameter=get_activity_performed_parameter())
                activity_performed.value = activity.id
                activity_performed.save()
        # FIXME: sender parameter doesn't really matter here, just pass self in as the sender
        update_active_experiments(self)
        for group in e.group_set.all():
            self.assertEqual(get_footprint_level(group).value, 2)
            self.assertEqual(average_points_per_person(group), 177)

class GroupActivityTest(BaseTest):
    def test_group_activity_json(self):
        e = self.experiment
        e.activate()
        e.start_round()
        participant_group_relationship = ParticipantGroupRelationship.objects.filter(group__experiment=e)[0]
        # do every activity in level 1 for this particular participant
        activity_performed_parameter = get_activity_performed_parameter()
        current_round_data = e.current_round_data
        for activity in Activity.objects.filter(level=1):
            activity_performed = participant_group_relationship.participant_data_value_set.create(submitted=True, round_data=current_round_data, parameter=activity_performed_parameter)
            activity_performed.value = activity.id
            activity_performed.save()
        group_activity_json = get_group_activity_json(participant_group_relationship)
        group_activity_dict = json.loads(group_activity_json)
        chat_messages = group_activity_dict['chat_messages']
        recent_activity = group_activity_dict['recent_activity']
        self.assertEqual(0, len(chat_messages))
        self.assertEqual(5, len(recent_activity))
        test_message = "Midnight mushrumps"
        response = self.client.post('/lighterprints/api/message', {
            'participant_group_id': participant_group_relationship.id,
            'message': test_message,
            })
# should not be allowed to post when not logged in
        self.assertEqual(response.status_code, 302)
        self.client.login(username=participant_group_relationship.participant.email, password='test')
        response = self.client.post('/lighterprints/api/message', {
            'participant_group_id': participant_group_relationship.id,
            'message': test_message,
            })
# now it should be OK, logged in user
        self.assertEqual(response.status_code, 200)
        group_activity_json = get_group_activity_json(participant_group_relationship)
        group_activity_dict = json.loads(group_activity_json)
        chat_messages = group_activity_dict['chat_messages']
        recent_activity = group_activity_dict['recent_activity']
        self.assertEqual(1, len(chat_messages))
        self.assertEqual(chat_messages[0]['message'], test_message)
        self.assertEqual(5, len(recent_activity))

class ActivityTest(BaseTest):
    def perform_activities(self, activities=None):
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=self.experiment):
            activities = available_activities(participant_group_relationship)
            participant = participant_group_relationship.participant
            self.client.login(username=participant.email, password='test')
            for activity in activities:
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                expected_success = is_activity_available(activity, participant_group_relationship)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                    })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])

    def test_view(self):
        logger.debug("testing do activity view")
        e = self.experiment
        e.activate()
        e.start_round()
        activities = available_activities()
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            logger.debug("all available activities: %s", activities)
            participant = participant_group_relationship.participant
            self.client.login(username=participant.email, password='test')
            for activity in activities:
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                expected_success = is_activity_available(activity, participant_group_relationship)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                    })
                self.assertEqual(response.status_code, 200)
                json_object = json.loads(response.content)
                self.assertEqual(expected_success, json_object['success'])
                logger.debug("Initial do activity response: %s", response)
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
                logger.debug("json: %s", json_object)
                self.assertEqual(json_object['comment'], text)


class GreenButtonDataTest(BaseTest):
    test_filenames = [os.path.join('vcweb', 'lighterprints', 'fixtures', filename) for filename in ('decreasing_day1.xml', 'decreasing_day2.xml')]

    def setUp(self):
        super(GreenButtonDataTest, self).setUp(is_public=True)

    def verify(self, xmltree):
        logger.debug("xmltree: %s", xmltree)
        ns = { 'gb': 'http://naesb.org/espi' }
        interval_block = xmltree.find('//gb:IntervalBlock', namespaces=ns)
        interval_data = interval_block.find('gb:interval', namespaces=ns)
        total_interval_duration = int(interval_data.find('gb:duration', namespaces=ns).text)
        interval_start_from_epoch = int(interval_data.find('gb:start', namespaces=ns).text)
        interval_readings = interval_block.findall('gb:IntervalReading', namespaces=ns)
        self.assertTrue(len(interval_readings) > 1)
        for interval_reading in interval_readings:
            time_period = interval_reading.find('gb:timePeriod', namespaces=ns)
            duration = time_period.find('gb:duration', namespaces=ns)
            self.assertEquals(int(duration.text), 3600)



    def test_import(self):
        for filename in self.test_filenames:
            xmltree = etree.parse(open(filename))
            self.verify(xmltree)

class ActivityUnlockingTest(ActivityTest):

    def setUp(self):
        super(ActivityUnlockingTest, self).setUp(is_public=True)

    def test_activity_performed_unlocking(self):
        e = self.experiment
        e.activate()
        e.start_round()
        activities = initial_unlocked_activities()
        for pgr in self.participant_group_relationships:
            for activity_id in activities.values_list('id', flat=True):
                # do each activity 3 times
                for _ in range(3):
                    ParticipantRoundDataValue.objects.create(participant_group_relationship=pgr,
                            parameter=get_activity_performed_parameter(), int_value=activity_id)
        update_public_experiment(e)
        for pgr in self.participant_group_relationships:
            self.assertEquals(get_green_points(pgr), 330)
            unlocked_activities = get_unlocked_activities(pgr)
            self.assertEquals(len(unlocked_activities), 7)
            logger.debug("unlocked activities: %s", unlocked_activities)

    def test_level_unlocking(self):
        e = self.experiment
        e.activate()
        e.start_round()
        self.assertTrue(e.is_public)
        for pgr in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            self.assertEquals(get_unlocked_activities(pgr).count(), 3)
            self.assertEquals(pgr.participant_data_value_set.get(parameter=get_participant_level_parameter()).value, 1)
            self.assertEquals(get_participant_level(pgr), 1)
        self.perform_activities()
        for pgr in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            self.assertEquals(get_unlocked_activities(pgr).count(), 3)
            self.assertEquals(pgr.participant_data_value_set.get(parameter=get_participant_level_parameter()).value, 1)
            self.assertEquals(get_participant_level(pgr), 2)
        update_public_experiment(e)
        for pgr in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            self.assertEquals(get_unlocked_activities(pgr).count(), 4)
            self.assertEquals(pgr.participant_data_value_set.get(parameter=get_participant_level_parameter()).value, 2)
            self.assertEquals(get_participant_level(pgr), 2)

class GroupScoreTest(ActivityTest):
    def setUp(self):
        super(GroupScoreTest, self).setUp(is_public=True)
    def test_group_score(self):
        e = self.experiment
        e.activate()
        e.start_round()
        self.perform_activities()
        for group in e.group_set.all():
            average_points_per_person, total_points = get_group_score(group)
            self.assertEquals(average_points_per_person, 110)
            self.assertEquals(total_points, 550)


