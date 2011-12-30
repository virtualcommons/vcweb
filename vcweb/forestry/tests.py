from vcweb.core.models import (RoundConfiguration, Parameter, ParticipantRoundDataValue,
        GroupRoundDataValue, ParticipantExperimentRelationship, ParticipantGroupRelationship)
from vcweb.core.tests import BaseVcwebTest
from vcweb.forestry.models import *
import logging
logger = logging.getLogger(__name__)

class ForestryRoundSignalTest(BaseVcwebTest):

    def verify_resource_level(self, group, value=100):
        self.assertEqual(get_resource_level(group).value, value)

    def test_round_ended_signal(self):
        e = self.test_round_started_signal()
        self.verify_round_ended(e, lambda e: e.end_round(sender=forestry_sender))

    def test_round_started_signal(self):
        e = self.advance_to_data_round()
        e.start_round(sender=forestry_sender)
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def test_round_setup(self):
        e = self.advance_to_data_round()
        # manually invoke round_setup, otherwise start_round should work as
        # well (but that's tested in the signal tests)
        round_setup(e)
        for group in e.group_set.all():
            self.verify_resource_level(group)
        return e

    def verify_round_ended(self, e, end_round_func):
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.group_set.all():
            ds = get_harvest_decisions(group)
            self.verify_resource_level(group)
            self.assertEqual(len(ds), group.participant_set.count())
            for pgr in group.participant_group_relationship_set.all():
                pdv = ParticipantRoundDataValue.objects.get(
                        parameter=harvest_decision_parameter,
                        participant_group_relationship=pgr,
                        round_data=current_round_data
                        )
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.value = 5
                pdv.save()
        end_round_func(e)

    def test_round_ended(self):
        e = self.test_round_setup()
        self.verify_round_ended(e, lambda experiment: round_teardown(experiment))

class ForestryViewsTest(BaseVcwebTest):

    def test_get_template(self):
        e = self.experiment
        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ, template_name='quiz_23.html')
        e.current_round_sequence_number = rc.sequence_number
        self.assertEqual(e.current_round_template, 'forestry/quiz_23.html', 'should return specified quiz_template')

        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ)
        e.current_round_sequence_number = rc.sequence_number
        self.assertEqual(e.current_round_template, 'forestry/quiz.html', 'should return default quiz.html')

class TransferParametersTest(BaseVcwebTest):
    def test_transfer_parameters(self):
        def calculate_expected_resource_level(resource_level, harvested):
            after_harvest = max(resource_level - harvested, 0)
            return min(100, int(after_harvest + (after_harvest * .10)))

        e = self.advance_to_data_round()
        expected_resource_level = 100
        while True:
            e.start_round()
            current_round_configuration = e.current_round
            if should_reset_resource_level(current_round_configuration):
                logger.debug("resetting resource level for round %s, %d", current_round_configuration,
                        e.current_round_sequence_number)
                expected_resource_level = get_initial_resource_level(current_round_configuration)

            if current_round_configuration.is_playable_round:
                max_harvest_decision = get_max_harvest_decision(expected_resource_level)
                for pgr in e.participant_group_relationships:
                    self.assertEquals(get_resource_level(pgr.group).value, expected_resource_level)
                    set_harvest_decision(pgr, max_harvest_decision)

                expected_resource_level = calculate_expected_resource_level(expected_resource_level, max_harvest_decision * 5)

            e.end_round()
            for group in e.group_set.all():
                logger.debug("checking group: %s", group)
                self.assertEquals(get_resource_level(group).value, expected_resource_level)

            if e.has_next_round:
                e.advance_to_next_round()
            else:
                break

class ForestryParametersTest(BaseVcwebTest):
    '''
    FIXME: several of these can and should be lifted to core/tests.py
    '''
    def test_initialize_parameters_at_round_start(self):
        e = self.advance_to_data_round()
        e.start_round()
        current_round_data = e.current_round_data
        group_parameters = (get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter())
        for group in e.group_set.select_related(depth=1).all():
            for parameter in group_parameters:
                group_data_value = group.data_value_set.get(round_data=current_round_data, parameter=parameter)
                self.assertTrue(group_data_value.parameter in group_parameters)
                self.assertTrue(group_data_value)
# single participant data parameter, harvest decisions
            for pgr in group.participant_group_relationship_set.all():
                prdv = pgr.participant_data_value_set.get(round_data=current_round_data,
                        parameter=get_harvest_decision_parameter())
                self.assertTrue(prdv)
                self.assertEquals(prdv.parameter, get_harvest_decision_parameter())

    def test_get_set_harvest_decisions(self):
        e = self.advance_to_data_round()
        # generate harvest decisions
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.group_set.all():
            ds = get_harvest_decisions(group)
            self.assertEquals(len(ds), group.participant_set.count())
            for p in group.participant_set.all():
                pgr = ParticipantGroupRelationship.objects.get(participant=p, group=group)
                pdv, created = current_round_data.participant_data_value_set.get_or_create(
                        participant_group_relationship=pgr,
                        parameter=harvest_decision_parameter)
                self.assertFalse(created)
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.value = 3
                pdv.save()
            ds = get_harvest_decisions(group)
            self.assertTrue(ds)
            for hd in ds.all():
                self.assertEqual(hd.value, 3)

            for pgr in ParticipantGroupRelationship.objects.filter(group=group):
                set_harvest_decision(participant_group_relationship=pgr, value=5)

            for hd in ds.all():
                self.assertEqual(hd.value, 5)


    def test_simple_cache_parameters(self):
        def verify_cached_data(func):
            self.assertEqual(func(), func())
            self.assertEqual(id(func()), id(func()))
        caching_funcs = (get_harvest_decision_parameter, get_group_harvest_parameter, get_regrowth_parameter,
                get_resource_level_parameter, get_forestry_experiment_metadata)
        for i in range(0, 25):
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
                get_resource_level_parameter, get_forestry_experiment_metadata)
        for i in range(0, 25):
            for func in caching_funcs:
                verify_refreshed_data(func)

    def test_get_set_resource_level(self):
        e = self.advance_to_data_round()
        e.start_round()
        for group in e.group_set.all():
            resource_level = get_resource_level(group)
            self.assertTrue(resource_level.pk > 0)
            self.assertEqual(resource_level.value, 100)
            resource_level.value = 3
            resource_level.save()

        for group in e.group_set.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level.value, 3)

        for group in e.group_set.all():
            set_resource_level(group, 100)
            self.assertEqual(get_resource_level(group).value, 100)

        for group in e.group_set.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level.value, 100)

    def test_group_round_data(self):
        data_round_number = 1
        current_round_data = None
        for e in self.all_data_rounds():
            self.assertNotEqual(current_round_data, e.current_round_data)
            current_round_data = e.current_round_data
            for data_value in current_round_data.group_data_value_set.filter(parameter__name='resource_level'):
                self.assertTrue(data_value.pk > 0)
                self.assertEqual('resource_level', data_value.parameter.name)
                data_value.value = 50
                data_value.save()
                self.assertEqual(50, data_value.value)
                data_value.value = 100
                data_value.save()
                self.assertEqual(100, data_value.value)
            self.assertEqual(e.current_round_data.group_data_value_set.count(), GroupRoundDataValue.objects.filter(group__experiment=e, round_data=current_round_data).count())
            self.assertEqual(e.parameters(scope=Parameter.GROUP_SCOPE).count(), 3)
            data_round_number += 1

    def test_data_parameters(self):
        e = self.experiment
        # FIXME: horrible tests, improve
        self.assertEqual(6, e.parameters().count())
        for data_param in e.parameters(scope=Parameter.GROUP_SCOPE).all():
            logger.debug("inspecting data param %s" % data_param)
            self.assertEqual(data_param.type, 'int', 'Currently all group data parameters for the forestry experiment are ints.')


    def create_participant_data_values(self):
        e = self.experiment
        e.activate()
        current_round_data = e.current_round_data
        for data_param in e.parameters(scope=Parameter.PARTICIPANT_SCOPE).all():
            for p in self.participants:
                pexpr = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                pgroupr = ParticipantGroupRelationship.objects.get(group__experiment=e, participant=p)
                current_round_data.participant_data_value_set.create(participant_group_relationship=pgroupr, parameter=data_param, value=pexpr.sequential_participant_identifier * 2)
        return e

    def test_data_values(self):
        e = self.create_participant_data_values()
        num_participant_parameters = e.parameters(scope=Parameter.PARTICIPANT_SCOPE).count()
        self.assertEqual(e.participant_set.count() * num_participant_parameters, ParticipantRoundDataValue.objects.filter(round_data__experiment=e).count(),
                'There should be %s participants * %s total data parameters = %s' % (e.participant_set.count(), num_participant_parameters, e.participant_set.count() * num_participant_parameters))

    def test_data_value_conversion(self):
        e = self.create_participant_data_values()
        current_round_data = e.current_round_data
        for p in self.participants:
            participant_data_values = current_round_data.participant_data_value_set.filter(participant_group_relationship__participant=p)
            self.assertEqual(participant_data_values.count(), 1)
            pexpr = p.get_participant_experiment_relationship(e)
            logger.debug("relationship %s" % pexpr)
            for dv in participant_data_values.all():
                logger.debug("verifying data value %s" % dv)
                self.assertEqual(pexpr.sequential_participant_identifier * 2, dv.value)
                self.assertTrue(dv.value)
                self.assertEqual(dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.assertFalse(dv.string_value)
                self.assertFalse(dv.boolean_value)
                self.assertFalse(dv.float_value)
        e.advance_to_next_round()
        current_round_data = e.current_round_data
        self.assertEqual(10, ParticipantRoundDataValue.objects.filter(round_data=current_round_data).count())
