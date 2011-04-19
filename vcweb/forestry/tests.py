from vcweb.core.models import RoundConfiguration, Parameter, ParticipantRoundDataValue, GroupRoundDataValue, ParticipantExperimentRelationship, ParticipantGroupRelationship
from vcweb.core.tests import BaseVcwebTest
from vcweb.forestry.models import round_setup, round_teardown, get_resource_level, get_harvest_decision_parameter, get_harvest_decisions, forestry_sender
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
        for group in e.groups.all():
            self.verify_resource_level(group)
        return e

    def test_round_setup(self):
        e = self.advance_to_data_round()
        # manually invoke round_setup, otherwise start_round should work as
        # well (but that's tested in the signal tests)
        round_setup(e)
        for group in e.groups.all():
            self.verify_resource_level(group)
        return e

    def verify_round_ended(self, e, end_round_func):
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.verify_resource_level(group)
            self.assertEqual(len(ds), group.participants.count())
            for p in group.participants.all():
                pgr = ParticipantGroupRelationship.objects.get(group=group, participant=p)
                pdv = ParticipantRoundDataValue.objects.get(
                        parameter=harvest_decision_parameter,
                        participant_group_relationship=pgr,
                        round_data=current_round_data
                        )
                self.assertTrue(pdv.pk > 0)
                self.assertFalse(pdv.value)
                pdv.value = group.number % 5
                pdv.save()

        end_round_func(e)
        '''
        at round end all harvest decisions are tallied and subtracted from
        the final resource_level
        '''
        def expected_resource_level(group):
            after_harvests = 100 - ((group.number % 5) * group.size)
            after_regrowth = min(after_harvests + (after_harvests / 10), 100)
            return after_regrowth

        for group in e.groups.all():
            self.assertEqual(get_resource_level(group).value,
                    expected_resource_level(group))

        e.advance_to_next_round()
        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level.value, expected_resource_level(group))

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


'''
FIXME: several of these can and should be lifted to core/tests.py
'''
class ForestryParametersTest(BaseVcwebTest):

    def test_get_set_harvest_decisions(self):
        from vcweb.forestry.models import get_harvest_decisions, get_harvest_decision_parameter, set_harvest_decision
        e = self.advance_to_data_round()
        # generate harvest decisions
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.assertFalse(ds, 'there should not be any harvest decisions.')
            for p in group.participants.all():
                pgr = ParticipantGroupRelationship.objects.get(participant=p, group=group)
                pdv = current_round_data.participant_data_values.create(
                        participant_group_relationship=pgr,
                        parameter=harvest_decision_parameter)
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


    def test_cacheable(self):
        from vcweb.forestry.models import (get_group_harvest_parameter, get_regrowth_parameter, get_forestry_experiment_metadata, get_resource_level_parameter, cacheable)
        self.assertEqual(get_harvest_decision_parameter(), get_harvest_decision_parameter())
        self.assertEqual(get_group_harvest_parameter(), get_group_harvest_parameter())
        self.assertEqual(get_regrowth_parameter(), get_regrowth_parameter())
        self.assertEqual(get_forestry_experiment_metadata(), get_forestry_experiment_metadata())
        self.assertEqual(get_resource_level_parameter(), get_resource_level_parameter())
        self.assertEqual(len(cacheable.orm_cache), 5)


    def test_get_set_resource_level(self):
        from vcweb.forestry.models import get_resource_level, set_resource_level
        e = self.advance_to_data_round()

        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.assertTrue(resource_level.pk > 0)
            self.assertFalse(resource_level.value)
            resource_level.value = 3
            resource_level.save()

        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level.value, 3)

        for group in e.groups.all():
            set_resource_level(group, 100)
            self.assertEqual(get_resource_level(group).value, 100)

        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.assertEqual(resource_level.value, 100)

    def test_group_round_data(self):
        data_round_number = 1
        current_round_data = None
        for e in self.all_data_rounds():
            self.assertNotEqual(current_round_data, e.current_round_data)
            current_round_data = e.current_round_data
            for data_value in current_round_data.group_data_values.filter(parameter__name='resource_level'):
                # test string conversion
                logger.debug("current round data: pk:%s value:%s unicode:%s" % (data_value.pk, data_value.value, data_value))
                self.assertTrue(data_value.pk > 0)
                self.assertFalse(data_value.value)
                data_value.value = 100
                data_value.save()
                self.assertEqual(100, data_value.value)
                self.assertEqual('resource_level', data_value.parameter.name)
                data_value.value = 50
                data_value.save()
                self.assertEqual(50, data_value.value)

            self.assertEqual(e.current_round_data.group_data_values.count(), GroupRoundDataValue.objects.filter(experiment=e, round_data=current_round_data).count())
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
                current_round_data.participant_data_values.create(participant_group_relationship=pgroupr, parameter=data_param, value=pexpr.sequential_participant_identifier * 2)
        return e

    def test_data_values(self):
        e = self.create_participant_data_values()
        num_participant_parameters = e.parameters(scope=Parameter.PARTICIPANT_SCOPE).count()
        self.assertEqual(e.participants.count() * num_participant_parameters, ParticipantRoundDataValue.objects.filter(experiment=e).count(),
                             'There should be %s participants * %s total data parameters = %s' % (e.participants.count(), num_participant_parameters, e.participants.count() * num_participant_parameters))

    def test_data_value_conversion(self):
        e = self.create_participant_data_values()
        current_round_data = e.current_round_data
        for p in self.participants:
            participant_data_values = current_round_data.participant_data_values.filter(participant_group_relationship__participant=p)
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
        self.assertEqual(0, ParticipantRoundDataValue.objects.filter(round_data=current_round_data).count())
