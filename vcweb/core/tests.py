from django.test import TestCase
from vcweb.core import signals
from vcweb.core.models import Experiment, Experimenter, ExperimentConfiguration, \
    Participant, ParticipantExperimentRelationship, Group, ExperimentMetadata, \
    RoundConfiguration, Parameter, RoundParameterValue, GroupActivityLog
import logging

logger = logging.getLogger(__name__)

"""
base class for vcweb.core tests, sets up test fixtures for participants,
forestry_test_data, and a number of participants, experiments, etc.,
based on the forestry experiment
"""
class BaseVcwebTest(TestCase):
    fixtures = ['test_users_participants', 'forestry_test_data']

    def load_experiment(self):
        self.experiment = Experiment.objects.get(pk=1)
        return self.experiment

    def setUp(self):
        self.participants = Participant.objects.all()
        self.load_experiment()
        self.experimenter = Experimenter.objects.get(pk=1)
        self.experiment_metadata = ExperimentMetadata.objects.get(pk=1)
        self.experiment_configuration = ExperimentConfiguration.objects.get(pk=1)

    def create_new_round_configuration(self, round_type='PLAY', template_name=None):
        return RoundConfiguration.objects.create(experiment_configuration=self.experiment_configuration,
                sequence_number=(self.experiment_configuration.last_round_sequence_number + 1),
                round_type=round_type,
                template_name=template_name
                )

    def create_new_experiment(self):
        return Experiment.objects.create(experimenter=self.experimenter,
                experiment_configuration=self.experiment_configuration,
                experiment_metadata=self.experiment_metadata)

    def create_new_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        return Group.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True

class QueueTest(BaseVcwebTest):
    def test_ghettoq(self):
        from ghettoq.simple import Connection
        conn = Connection("database")
        queue = conn.Queue(name="chat_messages")
        for test_string in ('testing', '1-2-3', 'good gravy'):
            queue.put(test_string)
            self.failUnlessEqual(test_string, queue.get())

class ExperimentMetadataTest(BaseVcwebTest):
    namespace_regex = ExperimentMetadata.namespace_regex

    def create_experiment_metadata(self, namespace=None):
        return ExperimentMetadata(title="test title: %s" % namespace, namespace=namespace)

    def test_valid_namespaces(self):
        valid_namespaces = ('forestry/hooha', 'furestry', 'f', 'hallo/h', '/f',
                            'abcdefghijklmnopqrstuvwxyz1234567890/abcdefghijklmnopqrstuvwxyz1234567890',
                            )
        for namespace in valid_namespaces:
            self.failUnless(self.namespace_regex.match(namespace))
            em = self.create_experiment_metadata(namespace)
            em.save()

    def test_invalid_namespaces(self):
        from django.core.exceptions import ValidationError
        invalid_namespaces = ('#$what the!',
                              "$$!it's a trap!",
                              '/!@')
        for namespace in invalid_namespaces:
            em = self.create_experiment_metadata(namespace)
            self.failUnlessRaises(ValidationError, em.full_clean)
            self.failIf(self.namespace_regex.match(namespace))

    def test_unicode(self):
        em = self.create_experiment_metadata('test_unicode_namespace')
        em.save()
        self.failUnless(em.pk and (em.pk > 0), 'test unicode namespace experiment metadata record should have valid id now')
        self.failUnless(em.__unicode__())
        self.failUnlessRaises(ValueError, em.__unicode__().index, '{')
        logger.debug("unicode is %s" % em.__unicode__())


class ExperimentConfigurationTest(BaseVcwebTest):

    def test_final_sequence_number(self):
        e = self.experiment
        ec = e.experiment_configuration
        self.failUnlessEqual(ec.final_sequence_number, 3)
        self.failUnlessEqual(ec.final_sequence_number,
                ec.last_round_sequence_number)

class ExperimentTest(BaseVcwebTest):

    def round_started_test_handler(self, experiment_id=None, time=None, round_configuration_id=None, **kwargs):
        logger.debug("invoking round started test handler with args experiment_id:%i time:%s round_configuration_id:%s"
                     % (experiment_id, time, round_configuration_id))
        self.failUnlessEqual(experiment_id, self.experiment.pk)
        self.failUnlessEqual(round_configuration_id, self.experiment.current_round.id)
        self.failUnless(time, "time should be set")
        raise Exception

    def test_start_round(self):
        signals.round_started.connect(self.round_started_test_handler, sender=self)
        try:
            self.experiment.start_round(sender=self)
            self.fail("Should have raised an exception.")
        except Exception, e:
            logger.debug("expected exception raised: %s" % e)
            self.failUnless(self.experiment.is_running())

    def test_allocate_groups(self):
        self.experiment.allocate_groups(randomize=False)
        self.failUnlessEqual(self.experiment.groups.count(), 2, "should be 2 groups after non-randomized allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            group = p.get_group(self.experiment)
            self.failIf(participant_number <= 0 or participant_number > group.max_size)
            self.failUnlessEqual(participant_number % group.max_size, p.id % group.max_size)
            logger.debug("randomized participant number %i (id: %i)" % (participant_number, p.pk))

    def test_next_round(self):
        experiment = self.experiment
        round_number = experiment.current_round_sequence_number
        self.failUnless(round_number >= 0)
        self.failUnless(experiment.has_next_round)
        while (experiment.has_next_round):
            round_number += 1
            experiment.advance_to_next_round()
            self.failUnless(experiment.current_round_sequence_number == round_number)
            logger.debug("experiment successfully advanced to next round: %s" %
                    experiment.current_round)

    def test_increment_elapsed_time(self):
        experiment = self.experiment
        current_round_elapsed_time = experiment.current_round_elapsed_time
        self.failUnless(current_round_elapsed_time == 0)
        total_elapsed_time = experiment.total_elapsed_time
        self.failUnless(total_elapsed_time == 0)
        Experiment.objects.increment_elapsed_time(status='INACTIVE')
        experiment = self.load_experiment()
        self.failUnlessEqual(experiment.current_round_elapsed_time, current_round_elapsed_time + 1)
        self.failUnlessEqual(experiment.total_elapsed_time, total_elapsed_time + 1)


    def test_get_participant_number(self):
        self.experiment.allocate_groups()
        self.failUnlessEqual(self.experiment.groups.count(), 2, "Should have two groups after allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            self.failUnless(participant_number > 0, 'participant number should be greater than 0')
            logger.debug("participant number %i (id: %i)" % (participant_number, p.pk))

class GroupTest(BaseVcwebTest):
    def test_set_data_value_activity_log(self):
        e = self.experiment
        for g in e.groups.all():
            activity_log_counter = GroupActivityLog.objects.filter(group=g).count()
            for data_value in g.data_values.all():
                # XXX: pathological use of set_data_value, no point in doing it
                # this way since typical usage would do a lookup by name.
                g.set_data_value(parameter=data_value.parameter, value=10)
                activity_log_counter += 1
                self.failUnlessEqual(activity_log_counter, GroupActivityLog.objects.filter(group=g).count())

    def test_transfer_to_next_round(self):
        e = self.experiment
        parameter = e.experiment_metadata.parameters.create(scope=Parameter.GROUP_SCOPE,
                name='test_group_parameter', type='int',
                creator=e.experimenter)
        for g in e.groups.all():
            g.initialize()
            g.set_data_value(parameter=parameter, value=15)
            self.failUnlessEqual(g.get_data_value(parameter=parameter), 15)
            g.transfer_to_next_round(parameter)

        e.advance_to_next_round()
        for g in e.groups.all():
            self.failUnlessEqual(g.get_data_value(parameter=parameter), 15)



    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.create_new_group(max_size=10, experiment=self.experiment)
        count = 0;
        for p in self.participants:
            g.add_participant(p)
            count += 1
            self.assertTrue(g.participants)
            self.failUnlessEqual(g.participants.count(), count, "group.participants size should be %i" % count)
            self.failUnlessEqual(g.size, count, "group size should be %i" % count)


class ParticipantExperimentRelationshipTest(BaseVcwebTest):

    def test_participant_identifier(self):
        """ exercises the generation of participant_identifier """
        e = self.create_new_experiment()
        for p in self.participants:
            per = ParticipantExperimentRelationship.objects.create(participant=p,
                    experiment=e, created_by=self.experimenter.user)
            self.failUnless(per.id > 0)
            logger.debug("Participant identifier is %s - sequential id is %i"
                         % (per.participant_identifier, per.sequential_participant_identifier))
            self.failUnless(per.participant_identifier)
            self.failUnless(per.sequential_participant_identifier > 0)

        self.failUnlessEqual(e.participants.count(), self.participants.count())


class RoundConfigurationTest(BaseVcwebTest):

    def test_round_configuration_enums(self):
        self.failUnlessEqual(len(RoundConfiguration.ROUND_TYPES), 6, 'Currently 6 round types are supported')
        self.failUnlessEqual(RoundConfiguration.PRACTICE, 'PRACTICE')
        self.failUnlessEqual(RoundConfiguration.BASIC, 'BASIC')
        choices = RoundConfiguration.ROUND_TYPE_CHOICES
        logger.debug("choices are: %s" % choices)
        self.failUnlessEqual(len(choices), 6)
        for pair in choices:
            self.failUnless(pair[0] in RoundConfiguration.ROUND_TYPES.keys())
            self.failIf(pair[1].isupper())

    def test_get_set_parameter(self):
        e = self.experiment
        round_configuration = e.current_round
        name = 'initial.resource_level'
        round_configuration.set_parameter(name=name, value=501)
        self.failUnlessEqual(round_configuration.get_parameter_value(name), 501)
        self.failUnlessEqual(round_configuration.get_parameter(name).value, round_configuration.get_parameter_value(name))

    def test_parameterized_value(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value='14')
        self.failUnlessEqual(14, rp.int_value)


    def test_round_parameters(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        self.failUnless(p.pk > 0)
        self.failUnlessEqual(p.value_field_name, 'int_value')

        for val in (14, '14', 14.0, '14.0'):
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=val)
            self.failUnless(rp.pk > 0)
            self.failUnlessEqual(rp.value, 14)

        '''
        The type field in Parameter generates the value_field_name property by concatenating the name of the type with _value.
        '''
        sample_values_for_type = {'int':3, 'float':3.0, 'string':'ich bin ein mublumubla', 'boolean':True}
        for type in ('int', 'float', 'string', 'boolean'):

            p = Parameter.objects.create(scope='round', name="test_nonunique_round_parameter_%s" % type, type=type, creator=e.experimenter, experiment_metadata=e.experiment_metadata)
            self.failUnless(p.pk > 0)
            self.failUnlessEqual(p.value_field_name, '%s_value' % type)
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=sample_values_for_type[type])
            self.failUnlessEqual(rp.value, sample_values_for_type[type])


    def test_get_templates(self):
        e = self.experiment
        for round_type, data in RoundConfiguration.ROUND_TYPES.items():
            logger.debug("inspecting round type: %s with data %s" % (round_type, data))
            rc = self.create_new_round_configuration(round_type=round_type)
            e.current_round_sequence_number = rc.sequence_number
            self.failUnlessEqual(e.current_round_template, "%s/%s" % (e.namespace, data[1]), 'should have returned template for ' + data[0])
