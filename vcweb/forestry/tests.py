"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from vcweb.core.models import RoundConfiguration, DataValue, \
    ParticipantDataValue, ParticipantExperimentRelationship, Participant
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

    def test_get_all_data_parameters(self):
        e = self.experiment
        self.failUnlessEqual(2, len(e.data_parameters), 'Currently 2 data parameters')
        for data_param in e.data_parameters:
            self.failUnlessEqual(data_param.type, 'int', 'Currently all data parameters for the forestry experiment are ints.')

    def create_participant_data_values(self):
        e = self.experiment
        rc = e.current_round
        for data_param in e.data_parameters:
            for p in self.participants:
                pexpr = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                dv = ParticipantDataValue(parameter=data_param, value=pexpr.sequential_participant_identifier * 2, experiment=e, participant=p, round_configuration=rc)
                dv.save()

        return e

    def test_data_values(self):
        self.create_participant_data_values()
        e = self.experiment
        self.failUnlessEqual(e.participants.count() * e.data_parameters.count(), len(ParticipantDataValue.objects.filter(experiment=e)),
                             'There should be %s participants * %s total data parameters = %s' % (e.participants.count(), e.data_parameters.count(), e.participants.count() * e.data_parameters.count()))

    def test_data_value_conversion(self):
        self.create_participant_data_values()
        e = self.experiment
        for p in self.participants:
            self.failUnlessEqual(p.data_values.count(), 2)
            pexpr = p.get_participant_experiment_relationship(e)
            for dv in p.data_values.all():
                self.failUnlessEqual(pexpr.sequential_participant_identifier * 2, dv.value)
                self.failUnless(dv.value)
                self.failUnlessEqual(dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.failIf(dv.string_value)
                self.failIf(dv.boolean_value)
                self.failIf(dv.float_value)
        rc = e.advance_to_next_round().current_round
        self.failUnlessEqual(0, len(ParticipantDataValue.objects.filter(experiment=e, round_configuration=rc)))
