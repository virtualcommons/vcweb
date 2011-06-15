from django.test.client import RequestFactory, Client
from vcweb.core.tests import BaseVcwebTest

from vcweb.lighterprints.views import *

import logging
logger = logging.getLogger(__name__)

class BaseTest(BaseVcwebTest):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()


class ActivityViewTest(BaseTest):
    def test_list(self):
        response = self.client.get('/lighterprints/activity/list?format=json')
        logger.debug("response is: %s", response)
        self.assertEqual(response.status_code, 200)

