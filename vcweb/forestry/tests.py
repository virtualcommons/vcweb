from vcweb.core.models import RoundConfiguration, Parameter, RoundData, ParticipantRoundDataValue, ParticipantExperimentRelationship, GroupRoundDataValue
from vcweb.core.tests import BaseVcwebTest
from vcweb.forestry.models import round_setup, round_ended, get_resource_level, get_harvest_decision_parameter, get_harvest_decisions
import logging

logger = logging.getLogger(__name__)

class ForestryRoundSignalTest(BaseVcwebTest):


    def verify_resource_level(self, group):
        self.failUnlessEqual(get_resource_level(group).value, 100)

    def test_round_ended_signal(self):
        e = self.test_round_started_signal()
        self.verify_round_ended_semantics(e, lambda e: e.end_round())

    def test_round_started_signal(self):
        e = self.experiment
        e.activate().start_round()
        for group in e.groups.all():
            self.verify_resource_level(group)
        return e

    def test_round_setup(self):
        e = self.experiment
        e.allocate_groups()
# set up some harvest decisions
        round_setup(e)
        for group in e.groups.all():
            self.verify_resource_level(group)
        return e

    def verify_round_ended_semantics(self, e, end_round_func):
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.verify_resource_level(group)
            self.failUnlessEqual(len(ds), group.participants.count())
            for p in group.participants.all():
                pdv = ParticipantRoundDataValue.objects.get(
                        parameter=harvest_decision_parameter,
                        participant=p,
                        round_data=current_round_data
                        )
                self.failUnless(pdv.pk > 0)
                self.failIf(pdv.value)
                pdv.value = group.number % 5
                pdv.save()

        end_round_func(e)
        '''
        at round end all harvest decisions are tallied and subtracted from
        the final resource_level
        '''
        expected_resource_level = lambda group: 100 - ((group.number % 5) * group.size)
        for group in e.groups.all():
            self.failUnlessEqual(get_resource_level(group).value,
                    expected_resource_level(group))

        e.advance_to_next_round()
        for group in e.groups.all():
            resource_level = get_resource_level(group)
            self.failUnlessEqual(resource_level.value, expected_resource_level(group))
            '''
            2 groups, 2 rounds of data = 4 total group round data value
            objects.
            '''
            self.failUnlessEqual(GroupRoundDataValue.objects.count(), 4)


    def test_round_ended(self):
        e = self.test_round_setup()
        self.verify_round_ended_semantics(e, lambda experiment: round_ended(experiment))

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
        e.activate()
        # generate harvest decisions
        current_round_data = e.current_round_data
        harvest_decision_parameter = get_harvest_decision_parameter()
        for group in e.groups.all():
            ds = get_harvest_decisions(group)
            self.failIf(ds, 'there should not be any harvest decisions.')
            for p in group.participants.all():
                pdv = current_round_data.participant_data_values.create(
                        participant=p,
                        parameter=harvest_decision_parameter)
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
        e.activate()
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
        current_round_data = e.current_round_data
        for data_value in current_round_data.group_data_values.all():
            # test string conversion
            logger.debug("current round data: pk:%s value:%s unicode:%s" % (data_value.pk, data_value.value, data_value))
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
        self.failUnlessEqual(e.current_round_data.group_data_values.count(), GroupRoundDataValue.objects.filter(experiment=e).count())

        e.advance_to_next_round()
        self.failIfEqual(current_round_data, e.current_round_data)
        current_round_data = e.current_round_data
        for data_value in current_round_data.group_data_values.all():
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
        self.failUnlessEqual(current_round_data.group_data_values.count(), 2)
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
        current_round_data = e.current_round_data
        for data_param in e.parameters(scope=Parameter.PARTICIPANT_SCOPE).all():
            for p in self.participants:
                pexpr = ParticipantExperimentRelationship.objects.get(participant=p, experiment=e)
                dv = current_round_data.participant_data_values.create(participant=p, parameter=data_param, value=pexpr.sequential_participant_identifier * 2)
        return e

    def test_data_values(self):
        self.create_participant_data_values()
        e = self.experiment
        num_participant_parameters = e.parameters(scope=Parameter.PARTICIPANT_SCOPE).count()
        self.failUnlessEqual(e.participants.count() * num_participant_parameters, ParticipantRoundDataValue.objects.filter(experiment=e).count(),
                             'There should be %s participants * %s total data parameters = %s' % (e.participants.count(), num_participant_parameters, e.participants.count() * num_participant_parameters))

    def test_data_value_conversion(self):
        self.create_participant_data_values()
        e = self.experiment
        current_round_data = e.current_round_data
        for p in self.participants:
            participant_data_values = current_round_data.participant_data_values.filter(participant=p)
            self.failUnlessEqual(participant_data_values.count(), 1)
            pexpr = p.get_participant_experiment_relationship(e)
            logger.debug("relationship %s" % pexpr)
            for dv in participant_data_values.all():
                logger.debug("verifying data value %s" % dv)
                self.failUnlessEqual(pexpr.sequential_participant_identifier * 2, dv.value)
                self.failUnless(dv.value)
                self.failUnlessEqual(dv.int_value, pexpr.sequential_participant_identifier * 2)
                self.failIf(dv.string_value)
                self.failIf(dv.boolean_value)
                self.failIf(dv.float_value)
        e.advance_to_next_round()
        current_round_data = e.current_round_data
        self.failUnlessEqual(0, ParticipantRoundDataValue.objects.filter(round_data=current_round_data).count())
