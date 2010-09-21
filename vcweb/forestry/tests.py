"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from vcweb.core.models import RoundConfiguration
from vcweb.core.tests import BaseVcwebTest
from vcweb.forestry.views import get_template
import logging



logger = logging.getLogger('vcweb.forestry.tests')

class ForestryViewsTest(BaseVcwebTest):

    def test_get_quiz_template(self):
        e = self.experiment
        rc = self.create_new_round_configuration(round_type='QUIZ', quiz_template='quiz_4.html')
        e.current_round_number = rc.sequence_number
        self.failUnlessEqual(get_template(e), 'forestry/quiz_4.html', 'should return specified quiz_template')

        rc = self.create_new_round_configuration(round_type='QUIZ')
        e.current_round_number = rc.sequence_number
        self.failUnlessEqual(get_template(e), 'forestry/quiz.html', 'should return default quiz.html')













