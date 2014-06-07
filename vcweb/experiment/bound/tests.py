"""
boundary effects experiment unit tests
"""

import logging

from vcweb.core.tests import BaseVcwebTest
from vcweb.experiment.bound.models import *


logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):
    fixtures = ['bound_experiment_metadata',
                'forestry_experiment_metadata', 'bound_parameters', ]

    def create_harvest_decisions(self, value=10):
        for pgr in self.experiment.participant_group_relationships:
            set_harvest_decision(pgr, value, submitted=True)

    def setUp(self, **kwargs):
        super(BaseTest, self).setUp(
            experiment_metadata=get_experiment_metadata(), **kwargs)
        e = self.experiment
        cr = e.current_round
        cr.set_parameter_value(
            parameter=get_reset_resource_level_parameter(), boolean_value=True)
        logger.debug("boundary effects test loaded experiment %s", e)


class MultipleHarvestDecisionTest(BaseTest):

    def test_duplicate_harvest_decisions(self):
        e = self.experiment
        e.activate()
        self.create_harvest_decisions()
        current_round_data = e.current_round_data
        final_harvest_decision = 9
        for pgr in e.participant_group_relationships:
            set_harvest_decision(pgr, 7, submitted=True)
            set_harvest_decision(pgr, final_harvest_decision, submitted=True)
            ParticipantRoundDataValue.objects.filter(
                round_data=current_round_data,
                parameter=get_harvest_decision_parameter()).update(is_active=True)
        resource_levels = dict(
            [(g, get_resource_level_dv(g, current_round_data)) for g in e.groups])
        e.advance_to_next_round()
        current_round_data = e.current_round_data
        regrowth_rate = get_regrowth_rate(
            current_round_data.round_configuration)
        max_resource_level = get_max_resource_level(
            current_round_data.round_configuration)
        for g in e.groups:
            dv = get_resource_level_dv(g, current_round_data)
            previous_round_resource_level = resource_levels[g]
            self.assertTrue(previous_round_resource_level.int_value >
                            dv.int_value, "Resource level should have decreased")
            after_harvest = previous_round_resource_level.int_value - \
                (final_harvest_decision * g.size)
            regrowth = calculate_regrowth(
                after_harvest, regrowth_rate, max_resource_level)
            expected_resource_level = after_harvest + regrowth
            self.assertEqual(dv.int_value, int(expected_resource_level))
            logger.debug("previous round resource level %s, current resource level: %s",
                         previous_round_resource_level.int_value, dv.int_value)


class AdjustHarvestDecisionsTest(BaseTest):

    def test_adjust_harvest_decisions(self):
        e = self.experiment
        e.activate()
        for rl in range(30, 40):
            self.create_harvest_decisions()
            for g in e.groups:
                set_resource_level(g, rl)
            e.end_round()
            for g in e.groups:
                self.assertEqual(get_resource_level(g), 0)
            for pgr in self.participant_group_relationships:
                self.assertTrue(get_harvest_decision(pgr) <= 8)
            e.advance_to_next_round()


class MaxResourceLevelTest(BaseTest):

    def test_max_resource_level(self):
        e = self.experiment
        e.activate()
        self.assertEqual(get_max_resource_level(e.current_round), 5 * 3 * 20)


class InitialDataTest(BaseTest):

    def test_experiment_metadata(self):
        self.assertIsNotNone(get_experiment_metadata())

    def test_parameters(self):
        """ FIXME: disabled until we fix Parameter <-> ExperimentMetadata association
        expected_parameter_names = ('survival_cost', 'storage', 'player_status')
        for p in get_experiment_metadata().parameters:
            self.assertTrue(p.name in expected_parameter_names)
        """
