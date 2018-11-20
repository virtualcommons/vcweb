"""
boundary effects experiment unit tests
"""

import logging
import random

from vcweb.core.models import (GroupCluster, Experiment, ParticipantRoundDataValue)
from vcweb.core.tests import BaseVcwebTest
from .models import (get_experiment_metadata, set_harvest_decision, GroupRelationship, get_resource_level_dv,
                     get_regrowth_rate, calculate_regrowth, set_resource_level, get_resource_level,
                     get_harvest_decision_parameter, get_max_resource_level, get_harvest_decision,
                     get_max_harvest_decision)

logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):

    def load_experiment(self, **kwargs):
        ''' returns the AB treatment configured in the boundary effects data migration '''
        return Experiment.objects.filter(experiment_metadata=get_experiment_metadata()).first().clone()

    def create_harvest_decisions(self, value=10):
        for pgr in self.experiment.participant_group_relationships:
            set_harvest_decision(pgr, value, submitted=True)


class GroupClusterTest(BaseTest):

    def test_group_cluster_data_values(self):
        e = self.experiment
        e.activate()

    def test_group_cluster_configuration(self):
        e = self.experiment
        e.activate()
        while e.current_round.round_type != 'INSTRUCTIONS':
            e.advance_to_next_round()
        current_round = e.current_round
        self.assertTrue(current_round.create_group_clusters)
        self.assertTrue(current_round.randomize_groups)
        self.assertEqual(current_round.session_id, 'A')
        self.assertFalse(current_round.is_playable_round)
        e.advance_to_next_round()
        self.assertTrue(e.current_round.is_playable_round)
        self.assertEqual(e.current_round.session_id, 'A')
        for g in e.groups:
            other_group = g.get_related_group()
            self.assertNotEqual(g, other_group)
        self.assertEqual(8, e.number_of_participants)
        self.assertEqual(2, len(e.groups))
        self.assertEqual(
            len(e.groups), GroupRelationship.objects.filter(group__experiment=e).count())
        self.assertEqual(len(e.groups) / e.current_round.group_cluster_size,
                         GroupCluster.objects.filter(experiment=e).count())
        # FIXME: assumes single group cluster
        gc = GroupCluster.objects.get(experiment=e)
        for gr in GroupRelationship.objects.filter(group__experiment=e):
            self.assertEqual(gc, gr.cluster)


class MultipleHarvestDecisionTest(BaseTest):

    def test_duplicate_harvest_decisions(self):
        e = self.experiment
        self.advance_to_data_round()
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
        self.advance_to_data_round()
        resource_level = random.randint(10, 40)
        self.create_harvest_decisions()
        for g in e.groups:
            set_resource_level(g, resource_level)
            self.assertEqual(get_resource_level(g), resource_level)
        for pgr in self.participant_group_relationships:
            self.assertEqual(10, get_harvest_decision(pgr))
        e.advance_to_next_round()
        for g in e.groups:
            self.assertEqual(get_resource_level(g), 0)
        for pgr in self.participant_group_relationships:
            self.assertTrue(get_harvest_decision(pgr) <= 8)


class ParticipantTest(BaseTest):

    def test_harvest_decision(self):
        self.experiment.activate()
        max_harvest_decision = get_max_harvest_decision(
            self.experiment.experiment_configuration)
        for pgr in self.participant_group_relationships:
            self.login_participant(pgr.participant)
            response = self.get(self.experiment.participant_url)
            self.assertEqual(response.status_code, 200)
            harvest_decision = random.randint(0, max_harvest_decision)
            response = self.post(self.experiment.get_participant_url('submit-harvest-decision'),
                                 {'participant_group_id': pgr.pk, 'integer_decision': harvest_decision})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(harvest_decision, get_harvest_decision(pgr))
            # FIXME: parse & verify json response content

    def test_participate(self):
        for participant in self.participants:
            self.login_participant(participant)
            response = self.get(self.experiment.participant_url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue('dashboard' in response[
                            'Location'], 'inactive experiment should redirect to dashboard')
        self.experiment.activate()
        while self.experiment.has_next_round:
            for participant in self.participants:
                self.login_participant(participant)
                response = self.get(self.experiment.participant_url)
                self.assertEqual(response.status_code, 200)
            self.experiment.advance_to_next_round()


class MaxResourceLevelTest(BaseTest):

    def test_max_resource_level(self):
        self.advance_to_data_round()
        e = self.experiment
        self.assertEqual(get_max_resource_level(e.current_round), 120)
