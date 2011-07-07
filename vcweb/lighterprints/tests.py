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
        parameter = create_activity_performed_parameter()
# initialize participant carbon savings
        for participant_group_relationship in ParticipantGroupRelationship.objects.filter(group__experiment=e):
            for activity in Activity.objects.all():
                activity_performed, created = participant_group_relationship.participant_data_value_set.get_or_create(round_data=current_round_data, parameter=parameter)
                activity_performed.value = activity.pk
            logger.debug("activity performed %s (%s)", activity_performed, created)

