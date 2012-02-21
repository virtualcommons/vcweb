from django.test import TestCase
from vcweb.core import signals
from vcweb.core.models import (Experiment, Experimenter, ExperimentConfiguration,
    Participant, ParticipantExperimentRelationship, ParticipantGroupRelationship, Group,
    ExperimentMetadata, RoundConfiguration, Parameter, RoundParameterValue,
    GroupActivityLog)
import logging

logger = logging.getLogger(__name__)

class BaseVcwebTest(TestCase):
    """
    base class for vcweb.core tests, sets up test fixtures for participants,
    forestry_test_data, and a number of participants, experiments, etc.,
    based on the forestry experiment
    """
    fixtures = ['test_users_participants', 'forestry_test_data']

    def load_experiment(self, experiment_metadata=None, **kwargs):
        if experiment_metadata is None:
# default to the Forestry experiment if no metadata is passed in
            experiment = Experiment.objects.get(pk=1).clone()
        else:
            experiment = self.create_new_experiment(experiment_metadata, **kwargs)
        if experiment.participant_set.count() == 0:
            experiment.setup_test_participants(email_suffix='asu.edu', count=10)
        logger.debug("loaded %s", experiment)
        self.experiment = experiment
        return experiment

    @property
    def experiment_metadata(self):
        return self.experiment.experiment_metadata

    @property
    def experiment_configuration(self):
        return self.experiment.experiment_configuration

    @property
    def experimenter(self):
        return self.experiment.experimenter

    @property
    def participants(self):
        return self.experiment.participant_set.all()

    def create_new_experiment(self, experiment_metadata, experimenter=None):
        if experimenter is None:
            experimenter = Experimenter.objects.get(pk=1)
        experiment_configuration = ExperimentConfiguration.objects.create(experiment_metadata=experiment_metadata,
                name='Test Experiment Configuration', creator=experimenter)
        for index in xrange(1, 10):
            experiment_configuration.round_configuration_set.create(sequence_number=index)
        return Experiment.objects.create(experimenter=self.experimenter,
                experiment_metadata=experiment_metadata, experiment_configuration=experiment_configuration)


    def setUp(self):
        self.load_experiment()

    def advance_to_data_round(self):
        self.experiment.activate()
        while self.experiment.has_next_round:
            if self.experiment.current_round.is_playable_round:
                return self.experiment
            self.experiment.advance_to_next_round()

    def all_data_rounds(self):
        self.experiment.activate()
        while self.experiment.has_next_round:
            if self.experiment.current_round.is_playable_round:
                yield self.experiment
            self.experiment.advance_to_next_round()

    def create_new_round_configuration(self, round_type='REGULAR', template_name=None):
        return RoundConfiguration.objects.create(experiment_configuration=self.experiment_configuration,
                sequence_number=(self.experiment_configuration.last_round_sequence_number + 1),
                round_type=round_type,
                template_name=template_name
                )

    def create_new_parameter(self, name='vcweb.test.parameter', scope='EXPERIMENT_SCOPE', parameter_type='string'):
        return self.experiment_metadata.parameter_set.create(creator=self.experimenter, name=name, scope=scope, type=parameter_type)


    def create_new_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        return Group.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True



class ExperimentMetadataTest(BaseVcwebTest):
    namespace_regex = ExperimentMetadata.namespace_regex

    def create_experiment_metadata(self, namespace=None):
        return ExperimentMetadata(title="test title: %s" % namespace, namespace=namespace)

    def test_valid_namespaces(self):
        valid_namespaces = ('forestry/hooha', 'furestry', 'f', 'hallo/h', '/f',
                            'abcdefghijklmnopqrstuvwxyz1234567890/abcdefghijklmnopqrstuvwxyz1234567890',
                            )
        for namespace in valid_namespaces:
            self.assertTrue(self.namespace_regex.match(namespace))
            em = self.create_experiment_metadata(namespace)
            em.save()

    def test_invalid_namespaces(self):
        from django.core.exceptions import ValidationError
        invalid_namespaces = ('#$what the!',
                              "$$!it's a trap!",
                              '/!@')
        for namespace in invalid_namespaces:
            em = self.create_experiment_metadata(namespace)
            self.assertRaises(ValidationError, em.full_clean)
            self.assertFalse(self.namespace_regex.match(namespace))

    def test_unicode(self):
        em = self.create_experiment_metadata('test_unicode_namespace')
        em.save()
        self.assertTrue(em.pk and (em.pk > 0), 'test unicode namespace experiment metadata record should have valid id now')
        self.assertTrue(unicode(em))
        #self.assertRaises(ValueError, unicode(em).index, '{')


class ExperimentConfigurationTest(BaseVcwebTest):
    def test_final_sequence_number(self):
        e = self.experiment
        ec = e.experiment_configuration
        self.assertEqual(ec.final_sequence_number, ec.last_round_sequence_number)

class ExperimentTest(BaseVcwebTest):
    def round_started_test_handler(self, experiment=None, time=None, round_configuration=None, **kwargs):
        logger.debug("invoking round started test handler with args experiment:%s time:%s round_configuration_id:%s", experiment, time, round_configuration)
        self.assertEqual(experiment, self.experiment)
        self.assertEqual(round_configuration, self.experiment.current_round)
        self.assertTrue(time, "time should be set")
        raise AssertionError

    def test_start_round(self):
        signals.round_started.connect(self.round_started_test_handler, sender=self)
        with self.assertRaises(AssertionError):
            self.experiment.start_round(sender=self)
        self.assertTrue(self.experiment.is_active)

    def test_group_allocation(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        logger.debug("experiment participants is %s", experiment.participant_set.all())
        self.assertEqual(experiment.group_set.count(), 2, "there should be 2 groups after non-randomized allocation")
        self.assertEqual( 10, sum([group.participant_set.count() for group in experiment.group_set.all()]) )

    def test_participant_numbering(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        for pgr in ParticipantGroupRelationship.objects.by_experiment(experiment):
            participant_number = pgr.participant_number
            group = pgr.group
            self.assertTrue(0 < participant_number <= group.max_size)
            # FIXME: this relies on the fact that non-randomized group allocation will match the auto increment pk
            # generation for the participants.  Remove?
            self.assertEqual(participant_number % group.max_size, pgr.participant.pk % group.max_size)

    def test_next_round(self):
        experiment = self.experiment
        round_number = experiment.current_round_sequence_number
        self.assertTrue(round_number >= 0)
        self.assertTrue(experiment.has_next_round)
        while (experiment.has_next_round):
            round_number += 1
            experiment.advance_to_next_round()
            self.assertTrue(experiment.current_round_sequence_number == round_number)

    def test_increment_elapsed_time(self):
        experiment = self.experiment
        current_round_elapsed_time = experiment.current_round_elapsed_time
        self.assertTrue(current_round_elapsed_time == 0)
        total_elapsed_time = experiment.total_elapsed_time
        self.assertTrue(total_elapsed_time == 0)
        delta = 120
        Experiment.objects.increment_elapsed_time(status=experiment.status, amount=delta)
        experiment = Experiment.objects.get(pk=self.experiment.pk)
        self.assertEqual(experiment.current_round_elapsed_time, current_round_elapsed_time + delta)
        self.assertEqual(experiment.total_elapsed_time, total_elapsed_time + delta)

    def test_instructions_round_parameters(self):
        e = self.experiment
        e.activate()
        e.start_round()
        # instructions round
        current_round_data = e.current_round_data
        self.assertEqual(current_round_data.group_data_value_set.count(), 0)
        self.assertEqual(current_round_data.participant_data_value_set.count(), 0)

    def test_playable_round(self):
        e = self.advance_to_data_round()
        e.start_round()
        current_round_data = e.current_round_data
        for group in e.group_set.all():
            for parameter in group.data_parameters.all():
                group_data_value, created = current_round_data.group_data_value_set.get_or_create(group=group,
                        parameter=parameter)
                self.assertFalse(created)
            for pgr in group.participant_group_relationship_set.all():
                for parameter in e.parameters(scope=Parameter.PARTICIPANT_SCOPE):
                    participant_data_value, created = current_round_data.participant_data_value_set.get_or_create(participant_group_relationship=pgr,
                            parameter=parameter)
                    self.assertFalse(created)

class GroupTest(BaseVcwebTest):
    def test_set_data_value_activity_log(self):
        e = self.advance_to_data_round()
        test_data_value = 10
        for g in e.group_set.all():
            activity_log_counter = GroupActivityLog.objects.filter(group=g).count()
            for data_value in g.data_value_set.all():
                # XXX: pathological use of set_data_value, no point in doing it
                # this way since typical usage would do a lookup by name.
                g.set_data_value(parameter=data_value.parameter, value=test_data_value)
                activity_log_counter += 1
                self.assertEqual(activity_log_counter, GroupActivityLog.objects.filter(group=g).count())
                self.assertEqual(g.get_scalar_data_value(parameter=data_value.parameter), test_data_value)

    def test_transfer_to_next_round(self):
        parameter = self.create_new_parameter(scope=Parameter.GROUP_SCOPE, name='test_group_parameter', parameter_type='int')
        test_data_value = 37
        e = self.experiment
        first_pass = True
        while e.has_next_round:
            if first_pass:
                for g in e.group_set.all():
                    g.set_data_value(parameter=parameter, value=test_data_value)
                    self.assertEqual(g.get_data_value(parameter=parameter).value, test_data_value)
                    self.assertEqual(g.get_scalar_data_value(parameter=parameter), test_data_value)
                    g.transfer_to_next_round(parameter)
                first_pass = False
            else:
                for g in e.group_set.all():
                    self.assertEqual(g.get_data_value(parameter=parameter).value, test_data_value)
                    self.assertEqual(g.get_scalar_data_value(parameter=parameter), test_data_value)
                    g.transfer_to_next_round(parameter)
            e.advance_to_next_round()



    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.create_new_group(max_size=10, experiment=self.experiment)
        count = 0;
        logger.debug("self participants: %s (%s)", self.participants, len(self.participants))
        for p in self.participants:
            g = g.add_participant(p)
            count += 1
            if count > 10:
                count = count % 10
            self.assertEqual(g.participant_set.count(), count, "group.participant_set count should be %i" % count)
            self.assertEqual(g.size, count, "group size should be %i" % count)


class ParticipantExperimentRelationshipTest(BaseVcwebTest):

    def test_participant_identifier(self):
        """ exercises the generation of participant_identifier """
        e = self.experiment.clone()
        for p in self.participants:
            per = ParticipantExperimentRelationship.objects.create(participant=p,
                    experiment=e, created_by=self.experimenter.user)
            self.assertTrue(per.id > 0)
            logger.debug("Participant identifier is %s - sequential id is %i", per.participant_identifier, per.sequential_participant_identifier)
            self.assertTrue(per.participant_identifier)
            self.assertTrue(per.sequential_participant_identifier > 0)

        self.assertEqual(e.participant_set.count(), self.participants.count())


class RoundConfigurationTest(BaseVcwebTest):

    def test_round_configuration_enums(self):
        self.assertEqual(len(RoundConfiguration.ROUND_TYPES), len(RoundConfiguration.ROUND_TYPES_DICT))
        self.assertEqual(RoundConfiguration.PRACTICE, 'PRACTICE')
        self.assertEqual(RoundConfiguration.REGULAR, 'REGULAR')
        choices = RoundConfiguration.ROUND_TYPE_CHOICES
        self.assertEqual(len(choices), len(RoundConfiguration.ROUND_TYPES_DICT))
        for pair in choices:
            self.assertTrue(pair[0] in RoundConfiguration.ROUND_TYPES_DICT.keys())
            self.assertTrue(pair[0] in RoundConfiguration.ROUND_TYPES)
            self.assertFalse(pair[1].isupper())

    def test_get_set_parameter(self):
        e = self.experiment
# current_round is instructions, with no available parameters.
        round_configuration = e.current_round
        name = 'initial_resource_level'
        round_configuration.set_parameter(name=name, value=501)
        self.assertEqual(round_configuration.get_parameter_value(name), 501)
        self.assertEqual(round_configuration.get_parameter(name).value, round_configuration.get_parameter_value(name))

    def test_parameterized_value(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value='14')
        self.assertEqual(14, rp.int_value)


    def test_round_parameters(self):
        e = self.experiment
        p = Parameter.objects.create(scope='round', name='test_round_parameter', type='int', creator=e.experimenter, experiment_metadata=e.experiment_metadata)
        self.assertTrue(p.pk > 0)
        self.assertEqual(p.value_field_name, 'int_value')

        for val in (14, '14', 14.0, '14.0'):
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=val)
            self.assertTrue(rp.pk > 0)
            self.assertEqual(rp.value, 14)

        '''
        The type field in Parameter generates the value_field_name property by concatenating the name of the type with _value.
        '''
        sample_values_for_type = {'int':3, 'float':3.0, 'string':'ich bin ein mublumubla', 'boolean':True}
        for type in ('int', 'float', 'string', 'boolean'):

            p = Parameter.objects.create(scope='round', name="test_nonunique_round_parameter_%s" % type, type=type, creator=e.experimenter, experiment_metadata=e.experiment_metadata)
            self.assertTrue(p.pk > 0)
            self.assertEqual(p.value_field_name, '%s_value' % type)
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round, value=sample_values_for_type[type])
            self.assertEqual(rp.value, sample_values_for_type[type])


    def test_get_templates(self):
        e = self.experiment
        for round_type, data in RoundConfiguration.ROUND_TYPES_DICT.items():
            logger.debug("inspecting round type: %s with data %s", round_type, data)
            rc = self.create_new_round_configuration(round_type=round_type)
            e.current_round_sequence_number = rc.sequence_number
            self.assertEqual(e.current_round_template, "%s/%s" % (e.namespace, data[1]), 'should have returned template for ' + data[0])


class GraphDatabaseTest(TestCase):
    def test_create_participant(self):
        from vcweb.core.graph import create_participant, create_activity,get_participant,get_activity
        usernames = []
        activity_names = []
        for i in range(1,10):
            username = 'test'+str(i)+'@asu.edu'
            usernames.append(username)
            try:
                create_participant(i, username)        
            except ValueError:
                logger.warning("Participant %s already exists", username)
        for i in range(1,15):
            name = 'activity'+str(i)
            activity_names.append(name)
            try:
                create_activity(i, name)
            except ValueError:
                logger.warning("Activity %s already exists", name)
            
        for i in range(1, 10):
            self.assertEqual(get_participant(i)["username"],usernames[i-1])
        for i in range(1, 15):
            self.assertEqual(get_activity(i)["name"],activity_names[i-1])


