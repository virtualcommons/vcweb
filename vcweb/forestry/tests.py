"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from vcweb.core.models import RoundConfiguration, DataValue, \
    ParticipantDataValue, ParticipantExperimentRelationship, Participant, \
    RoundParameter, Parameter, GroupRoundData, GroupRoundDataValue
from vcweb.core.tests import BaseVcwebTest
import logging



logger = logging.getLogger('vcweb.forestry.tests')

class ForestryViewsTest(BaseVcwebTest):

    def test_get_template(self):
        e = self.experiment
        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ, template_name='quiz_23.html')
        e.current_round_sequence_number = rc.sequence_number
        self.failUnlessEqual(e.current_round_template, 'forestry/quiz_23.html', 'should return specified quiz_template')

        rc = self.create_new_round_configuration(round_type=RoundConfiguration.QUIZ)
        e.current_round_sequence_number = rc.sequence_number
        self.failUnlessEqual(e.current_round_template, 'forestry/quiz.html', 'should return default quiz.html')


class ForestryParametersTest(BaseVcwebTest):

    def test_parameterized_value(self):
        e = self.experiment
        p = Parameter(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        p.save()
        rp = RoundParameter(parameter=p, round_configuration=e.current_round, value='14')
        rp.save()
        self.failUnlessEqual(14, rp.int_value)


    def test_round_parameters(self):
        e = self.experiment
        p = Parameter(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        p.save()
        self.failUnless(p.pk > 0)
        self.failUnlessEqual(p.value_field, 'int_value')

        for val in (14, '14', 14.0, '14.0'):
            rp = RoundParameter(parameter=p, round_configuration=e.current_round, value=val)
            rp.save()
            self.failUnless(rp.pk > 0)
            self.failUnlessEqual(rp.value, 14)

        '''
        The type field in Parameter generates the value_field property by concatenating the name of the type with _value.     
        '''
        sample_values_for_type = {'int':3, 'float':3.0, 'string':'ich bin ein mublumubla', 'boolean':True}
        for type in ('int', 'float', 'string', 'boolean'):
            p = Parameter(scope='round', name='test_nonunique_round_parameter', type=type, creator=e.experimenter, experiment_metadata=e.experiment_metadata)
            p.save()
            self.failUnless(p.pk > 0)
            self.failUnlessEqual(p.value_field, '%s_value' % type)
            rp = RoundParameter(parameter=p, round_configuration=e.current_round, value=sample_values_for_type[type])
            rp.save()
            self.failUnlessEqual(rp.value, sample_values_for_type[type])


    def test_group_round_data(self):
        e = self.experiment
        e.allocate_groups()
        for g in e.groups.all():
            for data_value in g.get_current_round_data().all():
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
            for data_value in g.get_current_round_data().all():
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




        self.failUnlessEqual(e.get_group_data_parameters().count(), 1)

    def test_data_parameters(self):
        e = self.experiment
        self.failUnlessEqual(2, len(e.parameters), 'Currently 2 data parameters')
        for data_param in e.parameters:
            logger.debug("inspecting data param %s" % data_param)
            self.failUnlessEqual(data_param.type, 'int', 'Currently all data parameters for the forestry experiment are ints.')


    def create_participant_data_values(self):
        e = self.experiment
        rc = e.current_round
        for data_param in e.parameters:
            for p in self.participants:
                pexpr = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                dv = ParticipantDataValue(parameter=data_param, value=pexpr.sequential_participant_identifier * 2, experiment=e, participant=p, round_configuration=rc)
                dv.save()

        return e

    def test_data_values(self):
        self.create_participant_data_values()
        e = self.experiment
        self.failUnlessEqual(e.participants.count() * e.parameters.count(), len(ParticipantDataValue.objects.filter(experiment=e)),
                             'There should be %s participants * %s total data parameters = %s' % (e.participants.count(), e.parameters.count(), e.participants.count() * e.parameters.count()))

    def test_data_value_conversion(self):
        self.create_participant_data_values()
        e = self.experiment
        for p in self.participants:
            self.failUnlessEqual(p.data_values.count(), 2)
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
