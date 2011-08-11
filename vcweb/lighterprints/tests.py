from django.test.client import RequestFactory, Client

from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import ParticipantGroupRelationship
from vcweb.lighterprints.views import *
from vcweb.lighterprints.models import *

import logging
logger = logging.getLogger(__name__)

class BaseTest(BaseVcwebTest):
    def setUp(self):
        super(BaseTest, self).setUp()
        self.client = Client()
        self.factory = RequestFactory()
        experiment_metadata = get_lighterprints_experiment_metadata()
        self.load_experiment(experiment_metadata=experiment_metadata)


class ActivityViewTest(BaseTest):
    def test_list(self):
        response = self.client.get('/lighterprints/activity/list?format=json')
        logger.debug("response is: %s", response)
        self.assertEqual(response.status_code, 200)


class UpdateLevelTest(BaseTest):
    def test_daily_carbon_savings(self):
        e = self.experiment
        e.activate()
        e.start_round()
        current_round_data = e.current_round_data
        activity_performed_parameter = create_activity_performed_parameter()
# initialize participant carbon savings
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            for activity in Activity.objects.filter(level=1):
                activity_performed = participant_group_relationship.participant_data_value_set.create(round_data=current_round_data, parameter=activity_performed_parameter, experiment=e)
                activity_performed.value = activity.id
                activity_performed.save()
        # FIXME: sender parameter doesn't really matter here, just pass self in as the sender
        update_active_experiments(self)
        for group in e.group_set.all():
            self.assertEqual(get_carbon_footprint_level(group).value, 2)
            self.assertEqual(get_daily_carbon_savings(group), Decimal('55.70'))

class GroupActivityTest(BaseTest):
    def test_group_activity_json(self):
        import simplejson as json
        e = self.experiment
        e.activate()
        e.start_round()
        participant_group_relationship = ParticipantGroupRelationship.objects.filter(group__experiment=e)[0]
        # do every activity in level 1 for this particular participant
        activity_performed_parameter = get_activity_performed_parameter()
        current_round_data = e.current_round_data
        for activity in Activity.objects.filter(level=1):
            activity_performed = participant_group_relationship.participant_data_value_set.create(submitted=True, round_data=current_round_data, parameter=activity_performed_parameter, experiment=e)
            activity_performed.value = activity.id
            activity_performed.save()
        group_activity_json = get_group_activity_json(participant_group_relationship)
        group_activity_dict = json.loads(group_activity_json)
        chat_messages = group_activity_dict['chat_messages']
        recent_activity = group_activity_dict['recent_activity']
        self.assertEqual(0, len(chat_messages))
        self.assertEqual(5, len(recent_activity))
        response = self.client.post('/lighterprints/api/post-chat', {
            'participant_group_id': participant_group_relationship.id,
            'message': "Midnight mushrumps",
            })
        self.assertEqual(response.status_code, 200)
        group_activity_json = get_group_activity_json(participant_group_relationship)
        group_activity_dict = json.loads(group_activity_json)
        chat_messages = group_activity_dict['chat_messages']
        recent_activity = group_activity_dict['recent_activity']
        self.assertEqual(1, len(chat_messages))
        self.assertEqual(5, len(recent_activity))



class DoActivityTest(BaseTest):
    def test_view(self):
        logger.debug("testing do activity view")
        e = self.experiment
        e.activate()
        e.start_round()
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            logger.debug("all available activities: %s", available_activities())
            for activity_availability in available_activities():
                logger.debug("available activity: %s", activity_availability)
                activity = activity_availability.activity
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.id
                    })
                self.assertEqual(response.status_code, 200)
# try to do the same activity again
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_id': participant_group_relationship.id,
                    'activity_id': activity.pk
                    })
                self.assertEqual(response.status_code, 400)




