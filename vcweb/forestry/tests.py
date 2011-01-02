"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from vcweb.core.models import RoundConfiguration,Parameter,ParticipantDataValue,ParticipantExperimentRelationship,GroupRoundDataValue
from vcweb.core.tests import BaseVcwebTest
import logging

logger = logging.getLogger('vcweb.forestry.tests')

class ForestryGameLogicTest(BaseVcwebTest):

    def test_round_setup(self):
        e = self.experiment
        from vcweb.forestry.models import round_setup, get_resource_level
        e.start()
# set up some harvest decisions
        round_setup(e)
        for group in e.groups.all():
            self.failUnlessEqual(get_resource_level(group).value, 100)

    def test_round_ended(self):
        e = self.experiment
        e.start()
        from vcweb.forestry.models import round_setup, round_ended, get_resource_level, get_harvest_decision_parameter, get_harvest_decisions
        round_setup(e)
        current_round = e.current_round
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.failIf(ds, 'there should not be any harvest decisions.')
            for p in group.participants.all():
                pdv = ParticipantDataValue.objects.create(
                        participant=p,
                        round_configuration=current_round,
                        parameter=harvest_decision_parameter,
                        experiment=e
                        )
                self.failUnless(pdv.pk > 0)
                self.failIf(pdv.value)
                pdv.value = 3
                pdv.save()
        round_ended(e)


class ForestryViewsTest(BaseVcwebTest):

    def test_get_template(self):
        e = self.experiment
        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ, template_name='quiz_23.html')
        e.current_round_sequence_number = rc.sequence_number
        self.failUnlessEqual(e.current_round_template, 'forestry/quiz_23.html', 'should return specified quiz_template')

        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ)
        e.current_round_sequence_number = rc.sequence_number
        self.failUnlessEqual(e.current_round_template, 'forestry/quiz.html', 'should return default quiz.html')


'''
FIXME: several of these can and should be lifted to core/tests.py
'''
class ForestryParametersTest(BaseVcwebTest):

    def test_get_set_harvest_decisions(self):
        from vcweb.forestry.models import get_harvest_decisions, get_harvest_decision_parameter, set_harvest_decision
        e = self.experiment
        e.start()
        # generate harvest decisions
        current_round = e.current_round
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.failIf(ds, 'there should not be any harvest decisions.')
            for p in group.participants.all():
                pdv = ParticipantDataValue.objects.create(
                        participant=p,
                        round_configuration=current_round,
                        parameter=harvest_decision_parameter,
                        experiment=e
                        )
                self.failUnless(pdv.pk > 0)
                self.failIf(pdv.value)
                pdv.value = 3
                pdv.save()
            ds = get_harvest_decisions(group)
            self.failUnless(ds)
            for hd in ds.all():
                self.failUnlessEqual(hd.value, 3)

            for p in group.participants.all():
                set_harvest_decision(participant=p, experiment=e, value=5)

            for hd in ds.all():
                self.failUnlessEqual(hd.value, 5)



    def test_get_set_resource_level(self):
        from vcweb.forestry.models import get_resource_level, set_resource_level
        e = self.experiment
        e.start()
        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.failUnless(resource_level.pk > 0)
            self.failIf(resource_level.value)
            resource_level.value = 3
            resource_level.save()

        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.failUnlessEqual(resource_level.value, 3)

        for group in e.groups.all():
            set_resource_level(group, 100)
            self.failUnlessEqual(get_resource_level(group).value, 100)

        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.failUnlessEqual(resource_level.value, 100)

    def test_group_round_data(self):
        e = self.experiment
        e.allocate_groups()
        for g in e.groups.all():
            for data_value in g.current_round_data_values.all():
                # test string conversion
                logger.debug("current round data: %s" % data_value)
                self.failUnless(data_value.pk > 0)
                self.failIf(data_value.value)
                data_value.value = 100
                data_value.save()
                self.failUnlessEqual(100, data_value.value)
                self.failUnlessEqual('resource_level', data_value.parameter.name)
                data_value.value = 50
                data_value.save()
                self.failUnlessEqual(50, data_value.value)

        self.failUnlessEqual(GroupRoundDataValue.objects.filter(experiment=e).count(), 2)

        e.advance_to_next_round()
        for g in e.groups.all():
            for data_value in g.current_round_data_values.all():
                # test string conversion
                logger.debug("current round data: %s" % data_value)
                self.failUnless(data_value.pk > 0)
                self.failIf(data_value.value)
                data_value.value = 100
                data_value.save()
                self.failUnlessEqual(100, data_value.value)
                self.failUnlessEqual('resource_level', data_value.parameter.name)
                data_value.value = 50
                data_value.save()
                self.failUnlessEqual(50, data_value.value)

        self.failUnlessEqual(GroupRoundDataValue.objects.filter(experiment=e).count(), 4)
        self.failUnlessEqual(e.parameters(scope=Parameter.GROUP_SCOPE).count(), 1)

    def test_data_parameters(self):
        e = self.experiment
        self.failUnlessEqual(4, e.parameters().count(), 'Currently 4 group parameters')
        for data_param in e.parameters(scope=Parameter.GROUP_SCOPE).all():
            logger.debug("inspecting data param %s" % data_param)
            self.failUnlessEqual(data_param.type, 'int', 'Currently all data parameters for the forestry experiment are ints.')


    def create_participant_data_values(self):
        e = self.experiment
        rc = e.current_round
        for data_param in e.parameters(scope=Parameter.PARTICIPANT_SCOPE).all():
            for p in self.participants:
                pexpr = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                dv = ParticipantDataValue(parameter=data_param, value=pexpr.sequential_participant_identifier * 2, experiment=e, participant=p, round_configuration=rc)
                dv.save()

        return e

    def test_data_values(self):
        self.create_participant_data_values()
        e = self.experiment
        num_participant_parameters = e.parameters(scope=Parameter.PARTICIPANT_SCOPE).count()
        self.failUnlessEqual(e.participants.count() * num_participant_parameters, len(ParticipantDataValue.objects.filter(experiment=e)),
                             'There should be %s participants * %s total data parameters = %s' % (e.participants.count(), num_participant_parameters, e.participants.count() * num_participant_parameters))

    def test_data_value_conversion(self):
        self.create_participant_data_values()
        e = self.experiment
        for p in self.participants:
            self.failUnlessEqual(p.data_values.count(), 1)
            pexpr = p.get_participant_experiment_relationship(e)
            logger.debug("relationship %s" % pexpr)
            for dv in p.data_values.all():
                logger.debug("verifying data value %s" % dv)
                self.failUnlessEqual(pexpr.sequential_participant_identifier * 2, dv.value)
                self.failUnless(dv.value)
                self.failUnlessEqual(dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.failIf(dv.string_value)
                self.failIf(dv.boolean_value)
                self.failIf(dv.float_value)
        rc = e.advance_to_next_round().current_round
        self.failUnlessEqual(0, len(ParticipantDataValue.objects.filter(experiment=e, round_configuration=rc)))
