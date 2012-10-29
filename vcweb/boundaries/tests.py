"""
Tests for boundaries experiment
"""

from django.test import TestCase

from vcweb.boundaries.models import *

class InitialDataTest(TestCase):
    def test_experiment_metadata(self):
        self.assertIsNotNone(get_experiment_metadata())

    def test_parameters(self):
        ps = Parameter.objects.filter(experiment_metadata=get_experiment_metadata())
        expected_parameter_names = ('survival_cost', 'storage', 'player_status')
        for p in ps:
            self.assertTrue(p.name in expected_parameter_names)
            

