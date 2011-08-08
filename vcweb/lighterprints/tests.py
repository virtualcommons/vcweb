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
            for activity in Activity.objects.all():
                activity_performed = participant_group_relationship.participant_data_value_set.get(round_data=current_round_data, parameter=activity_performed_parameter, experiment=e)
                activity_performed.value = activity.id
                activity_performed.save()
            logger.debug("all activities performed: %s",
                    participant_group_relationship.participant_data_value_set.all())
        update_active_experiments(self)


class DoActivityTest(BaseTest):
    def test_view(self):
        logger.debug("testing do activity view")
        e = self.experiment
        create_activity_performed_parameter()
        e.activate()
        e.start_round()
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            logger.debug("all available activities: %s", available_activities())
            for activity_availability in available_activities():
                logger.debug("available activity: %s", activity_availability)
                activity = activity_availability.activity
                logger.debug("participant %s performing activity %s", participant_group_relationship.participant, activity)
                response = self.client.post('/lighterprints/api/do-activity', {
                    'participant_group_relationship_id': participant_group_relationship.id,
                    'activity_id': activity.id
                    })
                logger.debug("response %s", response)
                self.assertEqual(response.status_code, 200)


