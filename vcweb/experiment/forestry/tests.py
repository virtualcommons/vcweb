import logging
import random

from vcweb.core.models import (GroupRoundDataValue, ParticipantExperimentRelationship)
from vcweb.core.tests import BaseVcwebTest
from .models import *


logger = logging.getLogger(__name__)


class ForestryRoundSignalTest(BaseVcwebTest):

    def verify_resource_level(self, group, value=100):
        self.assertEqual(get_resource_level(group), value)

    def test_round_ended_signal(self):
        e = self.test_round_started_signal()
        self.verify_round_ended(
            e, lambda e: e.end_round(sender=EXPERIMENT_METADATA_NAME))

    def test_round_started_signal(self):
        e = self.advance_to_data_round()
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def test_round_setup(self):
        e = self.advance_to_data_round()
        # manually invoke round_setup, otherwise start_round should work as
        # well (but that's tested in the signal tests)
        round_started_handler(None, e)
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def verify_round_ended(self, e, end_round_func):
        round_data = e.get_round_data()
        e.end_round()
        harvest_decision_parameter = get_harvest_decision_parameter()
        rd = e.current_round_data
        for group in e.groups:
            ds = group.get_participant_data_values(
                parameter_name='harvest_decision', round_data=rd)
            self.verify_resource_level(group)
            self.assertEqual(len(ds), group.participant_set.count())
            for pgr in group.participant_group_relationship_set.all():
                pdv = ParticipantRoundDataValue.objects.get(
                    parameter=harvest_decision_parameter,
                    participant_group_relationship=pgr,
                    round_data=round_data
                )
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.update_int(5)
        end_round_func(e)

    def test_round_ended(self):
        e = self.test_round_setup()
        self.verify_round_ended(
            e, lambda experiment: round_ended_handler(None, experiment))


class TransferParametersTest(BaseVcwebTest):

    def test_transfer_parameters(self):
        def calculate_expected_resource_level(resource_level, harvested):
            after_harvest = max(resource_level - harvested, 0)
            return min(100, int(after_harvest + (after_harvest * .10)))

        e = self.advance_to_data_round()
        expected_resource_level = 100
        while e.has_next_round:
            current_round_configuration = e.current_round
            if should_reset_resource_level(current_round_configuration, e):
                expected_resource_level = get_initial_resource_level(
                    current_round_configuration)

            if current_round_configuration.is_playable_round:
                max_harvest_decision = get_max_harvest_decision(
                    expected_resource_level)
                for pgr in e.participant_group_relationships:
                    self.assertEqual(
                        get_resource_level(pgr.group), expected_resource_level)
                    set_harvest_decision(pgr, max_harvest_decision)
                expected_resource_level = calculate_expected_resource_level(
                    expected_resource_level, max_harvest_decision * 5)

            e.end_round()
            for group in e.groups:
                self.assertEqual(get_resource_level(
                    group), expected_resource_level, "Group resource levels were not equal")
            e.advance_to_next_round()


class ForestryParametersTest(BaseVcwebTest):

    def test_parameters_set_at_round_end(self):
        e = self.advance_to_data_round()
        round_data = e.current_round_data
        group_parameters = (get_regrowth_parameter(
        ), get_group_harvest_parameter(), get_resource_level_parameter())
        # Ending the round to see if the round values are set or not
        e.end_round()
        for group in e.groups:
            for parameter in group_parameters:
                gdv = group.get_data_value(
                    round_data=round_data, parameter=parameter)
                self.assertTrue(gdv.parameter in group_parameters)
                self.assertTrue(gdv)
            # single participant data parameter, harvest decisions
            for pgr in group.participant_group_relationship_set.all():
                prdv = ParticipantRoundDataValue.objects.get(
                    participant_group_relationship=pgr, round_data=round_data, parameter=get_harvest_decision_parameter())
                self.assertTrue(prdv)
                self.assertEqual(
                    prdv.parameter, get_harvest_decision_parameter())

    def test_get_set_harvest_decisions(self):
        e = self.advance_to_data_round()
        # generate harvest decisions
        e.end_round()
        round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        harvest = 3
        for group in e.groups:
            ds = group.get_participant_data_values(
                parameter=harvest_decision_parameter, round_data=round_data)
            self.assertEqual(len(ds), group.participant_set.count())
            for p in group.participant_set.all():
                pgr = ParticipantGroupRelationship.objects.get(
                    participant=p, group=group)
                pdv, created = ParticipantRoundDataValue.objects.get_or_create(
                    round_data=round_data,
                    participant_group_relationship=pgr,
                    parameter=harvest_decision_parameter)
                self.assertFalse(created)
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.update_int(harvest)
                self.assertTrue(pdv.value)
                self.assertEqual(harvest, pdv.int_value)
                self.assertEqual(pdv.value, pdv.int_value)

            for hd in group.get_participant_data_values(parameter=harvest_decision_parameter, round_data=round_data):
                self.assertEqual(hd.int_value, harvest)

            for pgr in group.participant_group_relationship_set.all():
                set_harvest_decision(
                    participant_group_relationship=pgr, value=8)

            for hd in group.get_participant_data_values(parameter=harvest_decision_parameter, round_data=round_data):
                self.assertEqual(hd.value, 8)
                self.assertEqual(hd.value, hd.int_value)
        self.assertTrue(e.all_participants_submitted)

    def test_simple_cache_parameters(self):
        def verify_cached_data(func):
            self.assertEqual(func(), func())
            self.assertEqual(id(func()), id(func()))

        caching_funcs = (get_harvest_decision_parameter, get_group_harvest_parameter, get_regrowth_parameter,
                         get_resource_level_parameter, get_experiment_metadata)
        for _ in xrange(0, 25):
            for func in caching_funcs:
                verify_cached_data(func)

    def test_simple_cache_parameter_refresh(self):
        def verify_refreshed_data(func):
            self.assertEqual(func(), func())
            a = func()
            b = func(refresh=True)
            self.assertNotEqual(id(a), id(b))
            self.assertEqual(a, b)

        caching_funcs = (get_harvest_decision_parameter, get_group_harvest_parameter, get_regrowth_parameter,
                         get_resource_level_parameter, get_experiment_metadata)
        for _ in xrange(0, 25):
            for func in caching_funcs:
                verify_refreshed_data(func)

    def test_get_set_resource_level(self):
        e = self.advance_to_data_round()
        # should initially be 100
        for group in e.groups:
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level, 100)

        random_sequence = [random.randint(1, 100) for _ in xrange(0, 8)]
        for group in e.groups:
            for i in random_sequence:
                set_resource_level(group, i)
                self.assertEqual(get_resource_level(group), i)

    def test_group_round_data_values(self):
        round_data = None
        resource_level_parameter = Parameter.objects.get(name='resource_level')
        for e in self.all_data_rounds():
            self.assertNotEqual(round_data, e.current_round_data)
            round_data = e.current_round_data
            for dv in round_data.group_data_value_set.filter(parameter=resource_level_parameter):
                self.assertTrue(dv.pk > 0)
                self.assertEqual('resource_level', dv.parameter.name)
                dv.update_int(50)
                self.assertEqual(50, dv.int_value)
                self.assertEqual(dv.int_value, dv.value)
                dv.update_int(100)
                self.assertEqual(100, dv.int_value)
                self.assertEqual(dv.int_value, dv.value)
            self.assertEqual(round_data.group_data_value_set.count(),
                             GroupRoundDataValue.objects.filter(group__experiment=e, round_data=round_data).count())
            self.assertEqual(e.parameters(scope=Parameter.Scope.GROUP).count(
            ), 3, "There should be 3 group scoped parameters for the forestry experiment")

    def test_data_parameters(self):
        e = self.experiment
        self.assertEqual(e.experiment_metadata.parameters.count(), e.parameters().count(),
                         "experiment metadata parameters were not created properly")

    def test_data_value_conversion(self):
        e = self.experiment
        e.activate()
        round_data = e.current_round_data
        for data_param in e.parameters(scope=Parameter.Scope.PARTICIPANT):
            for p in self.participants:
                per = ParticipantExperimentRelationship.objects.get(
                    participant=p, experiment=e)
                pgr = ParticipantGroupRelationship.objects.get(group__experiment=e, participant=p)
                prdv = ParticipantRoundDataValue.objects.create(
                    round_data=round_data, participant_group_relationship=pgr, parameter=data_param)
                if data_param.type == 'int':
                    prdv.update_int(per.sequential_participant_identifier * 2)
        round_data = e.get_round_data()
        for p in self.participants:
            participant_data_values = round_data.participant_data_value_set.filter(
                participant_group_relationship__participant=p)
            self.assertEqual(participant_data_values.count(
            ), 2, "should only be 2 participant data values present, harvest decision and participant is ready %s" % participant_data_values)
            pexpr = e.get_participant_experiment_relationship(p)
            for dv in participant_data_values.filter(parameter__type='int'):
                self.assertEqual(
                    pexpr.sequential_participant_identifier * 2, dv.value)
                self.assertTrue(dv.value)
                self.assertEqual(
                    dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.assertEqual(
                    dv.int_value, dv.value, "int_value should be == value")
                self.assertFalse(dv.string_value)
                self.assertFalse(dv.boolean_value)
                self.assertFalse(dv.float_value)
        e.advance_to_next_round()
        self.assertEqual(10,
                         ParticipantRoundDataValue.objects.filter(round_data=round_data, parameter__type='int').count())
