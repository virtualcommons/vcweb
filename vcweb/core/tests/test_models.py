from datetime import datetime, timedelta
import random
import logging

from django.contrib.auth.models import User
from django.core import serializers

from .common import BaseVcwebTest, SubjectPoolTest
from .. import signals
from ..models import (ParticipantRoundDataValue, Participant, ParticipantExperimentRelationship,
                      BookmarkedExperimentMetadata, ParticipantGroupRelationship, ExperimentMetadata, Parameter,
                      RoundParameterValue, Institution, ExperimentSession, Invitation, ParticipantSignup, DefaultValue,)

logger = logging.getLogger(__name__)


class ExperimentMetadataTest(BaseVcwebTest):

    def create_experiment_metadata(self, namespace=None):
        return ExperimentMetadata(title="test title: %s" % namespace, namespace=namespace)

    def test_valid_namespaces(self):
        valid_namespaces = ('forestry_', 'furestry', 'f', 'oyo_yoy', 'f-s', '123_abc', 'abc_123',
                            'abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmnopqrstuvwxyz1234567890',
                            )
        for namespace in valid_namespaces:
            em = self.create_experiment_metadata(namespace)
            em.save()

    def test_invalid_namespaces(self):
        from django.core.exceptions import ValidationError

        invalid_namespaces = ('#$what the!',
                              "$!it's a trap!",
                              '/!@',
                              '123!',
                              'abc!',
                              '%123',
                              '%abc',
                              'abc%',
                              'abc/def',
                              )
        for namespace in invalid_namespaces:
            em = self.create_experiment_metadata(namespace)
            self.assertRaises(ValidationError, em.full_clean)

    def test_unicode(self):
        em = self.create_experiment_metadata('test_unicode_namespace')
        em.save()
        self.assertTrue(em.pk and (em.pk > 0),
                        'test unicode namespace experiment metadata record should have valid id now')
        self.assertTrue(unicode(em))
        #self.assertRaises(ValueError, unicode(em).index, '{')


class ExperimentConfigurationTest(BaseVcwebTest):

    def test_final_sequence_number(self):
        e = self.experiment
        ec = e.experiment_configuration
        self.assertEqual(
            ec.final_sequence_number, ec.last_round_sequence_number)

    def test_serialization_stream(self):
        pass

    def test_xml_serialization(self):
        e = self.experiment
        ec = e.experiment_configuration
        data = ec.serialize()
        self.assertIsNotNone(data)
        found = False
        for obj in serializers.deserialize("xml", data):
            self.assertIsNotNone(obj)
            entity = obj.object
            if entity.pk == ec.pk:
                found = True
        self.assertTrue(found)


class ExperimentTest(BaseVcwebTest):

    def round_started_test_handler(self, experiment=None, time=None, round_configuration=None, **kwargs):
        logger.debug("invoking round started test handler with args experiment:%s time:%s round configuration:%s",
                     experiment, time, round_configuration)
        if getattr(self, 'round_started_invoked', None):
            self.fail("Round started test handler invoked twice somehow")
        else:
            self.round_started_invoked = True
        self.assertEqual(experiment, self.experiment)
        self.assertEqual(round_configuration, self.experiment.current_round)
        self.assertTrue(time, "time should be set")
        # this ValueError shouldn't bubble up since we're using send_robust now
        raise ValueError(
            "Contrived ValueError from test round started handler")

    def test_clone(self):
        experiment = self.experiment
        experimenter = experiment.experimenter
        new_experimenter = self.create_experimenter()
        cloned_experiment = experiment.clone(new_experimenter)
        self.assertNotEqual(experiment, cloned_experiment)
        self.assertEqual(experiment.experiment_configuration, cloned_experiment.experiment_configuration)
        self.assertNotEqual(experimenter, cloned_experiment.experimenter)
        self.assertTrue(experiment.is_owner(experimenter.user))
        self.assertFalse(experiment.is_owner(new_experimenter.user))
        self.assertTrue(cloned_experiment.is_owner(new_experimenter.user))
        self.assertFalse(cloned_experiment.is_owner(experimenter.user))

    def test_activate(self):
        e = self.experiment
        self.assertFalse(e.is_active)
        self.assertEqual(len(e.groups), 0)
        self.assertEqual(len(e.participant_group_relationships), 0)
        e.activate()
        self.assertTrue(e.is_active)
        self.assertEqual(len(e.groups), 2)
        self.assertEqual(len(e.participant_group_relationships), 10)

    def test_clear(self):
        e = self.experiment
        e.activate()
        self.assertEqual(10, e.number_of_participants)
        self.assertEqual(2, len(e.groups))
        e.advance_to_next_round()
        self.assertEqual(e.current_round_data.round_configuration, e.current_round)
        e.clear()
        self.assertEqual(0, e.number_of_participants)
        self.assertEqual(0, len(e.groups))
        self.assertFalse(e.is_active or e.is_archived)

    def test_deactivate(self):
        e = self.experiment
        e.activate()
        self.assertTrue(1, e.round_data_set.count())
        self.assertTrue(2, len(e.groups))
        self.assertTrue(10, len(e.participant_group_relationships))
        self.assertTrue(e.is_active)
        e.advance_to_next_round()
        self.assertTrue(2, e.current_round_sequence_number)
        self.assertTrue(2, e.round_data_set.count())
        self.assertTrue(2, len(e.groups))
        self.assertTrue(10, len(e.participant_group_relationships))
        e.deactivate()
        self.assertFalse(e.is_active)
        self.assertEqual(10, e.number_of_participants)
        self.assertEqual(0, len(e.groups))
        self.assertEqual(0, len(e.participant_group_relationships))
        self.assertEqual(0, e.round_data_set.count())
        self.assertEqual(1, e.current_round_sequence_number)
        self.assertEqual(0, e.current_repeated_round_sequence_number)

    def test_restart(self):
        e = self.experiment
        e.activate()
        total_number_of_rounds = 1
        while e.has_next_round:
            total_number_of_rounds += 1
            e.advance_to_next_round()
        self.assertEqual(total_number_of_rounds, e.experiment_configuration.total_number_of_rounds)
        e.restart()
        self.assertTrue(e.is_active)
        self.assertEqual(10, e.number_of_participants)
        self.assertEqual(2, len(e.groups))
        self.assertEqual(10, len(e.participant_group_relationships))
        self.assertEqual(1, e.round_data_set.count())
        self.assertEqual(1, e.current_round_sequence_number)
        self.assertEqual(0, e.current_repeated_round_sequence_number)

    def test_archive(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            e.advance_to_next_round()
        self.assertFalse(e.has_next_round)
        self.assertFalse(e.is_completed)
        e.complete()
        self.assertTrue(e.is_completed)

    def test_start_round(self):
        signals.round_started.connect(
            self.round_started_test_handler, sender=self)
        self.experiment.start_round(sender=self)
        self.assertTrue(self.experiment.is_active)
        self.assertFalse(self.experiment.start_round(sender=self),
                         "subsequent start rounds should be no-ops that return false")

    def test_group_allocation(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        logger.debug(
            "experiment participants is %s", experiment.participant_set.all())
        self.assertEqual(experiment.group_set.count(
        ), 2, "there should be 2 groups after non-randomized allocation")
        self.assertEqual(
            10, sum([group.participant_set.count() for group in experiment.group_set.all()]))

    def test_participant_numbering(self):
        experiment = self.experiment
        experiment.allocate_groups(randomize=False)
        for pgr in ParticipantGroupRelationship.objects.for_experiment(experiment):
            participant_number = pgr.participant_number
            group = pgr.group
            self.assertTrue(0 < participant_number <= group.max_size)
            # FIXME: this relies on the fact that non-randomized group allocation will match the auto increment pk
            # generation for the participants.  Remove?
            self.assertEqual(
                participant_number % group.max_size, pgr.participant.pk % group.max_size)

    def test_next_round(self):
        experiment = self.experiment
        round_number = experiment.current_round_sequence_number
        self.assertTrue(round_number >= 0)
        self.assertTrue(experiment.has_next_round)
        while experiment.has_next_round:
            experiment.advance_to_next_round()
            if not experiment.should_repeat:
                round_number += 1
                self.assertTrue(
                    experiment.current_round_sequence_number == round_number)

    def test_elapsed_time(self):
        e = self.experiment
        e.activate()
        self.assertEqual(0, e.current_round_elapsed_time.seconds)
        self.assertTrue('Untimed round' in e.time_remaining_label)
        self.advance_to_data_round()
        self.assertTrue(e.time_remaining > 0)
        self.assertTrue(e.total_elapsed_time.total_seconds > 0)
        self.assertFalse(e.is_time_expired)
        self.assertTrue(int(e.time_remaining_label) > 0)

    def test_playable_round(self):
        # advance_to_next_round automatically starts the round
        e = self.advance_to_data_round()
        current_round_data = e.current_round_data
        logger.debug("current round data: %s", current_round_data)
        e.end_round()
        for group in e.groups:
            for parameter in group.parameters.all():
                gdvs = current_round_data.group_data_value_set.filter(parameter=parameter, group=group)
                if gdvs.exists():
                    logger.debug("testing parameter %s", parameter)
                    self.assertEqual(1, gdvs.count(), "Should only be a single group data value for parameter")
            for parameter in e.parameters(Parameter.Scope.PARTICIPANT):
                expected_size = group.size if parameter.name in (
                    'harvest_decision', 'participant_ready') else 0
                self.assertEqual(expected_size,
                                 ParticipantRoundDataValue.objects.for_group(group,
                                                                             round_data=current_round_data,
                                                                             parameter=parameter,
                                                                             ordered=False).count(),
                                 "unexpected %s, only harvest_decision and participant_ready should be auto-created" %
                                 parameter.name)


class GroupTest(BaseVcwebTest):

    def test_set_data_value(self):
        e = self.advance_to_data_round()
        test_data_value = 10
        for g in e.groups:
            for data_value in g.data_value_set.all():
                logger.debug("testing against data value %s", data_value)
                # XXX: pathological use of set_data_value, no point in doing it
                # this way since typical usage would do a lookup by name.
                g.set_data_value(parameter=data_value.parameter, value=test_data_value)
                self.assertEqual(g.get_scalar_data_value(parameter=data_value.parameter), test_data_value)

    def test_copy_to_next_round(self):
        parameter = self.create_parameter(scope=Parameter.Scope.GROUP,
                                          name='test_group_parameter',
                                          parameter_type='int')
        test_data_value = 37
        e = self.advance_to_data_round()
        first_pass = True
        data_value = None
        while e.has_next_round:
            for g in e.groups:
                if first_pass:
                    data_value = g.set_data_value(parameter=parameter, value=test_data_value)
                data_value = g.get_data_value(parameter=parameter)
                self.assertEqual(data_value.int_value, test_data_value)
                self.assertEqual(g.get_scalar_data_value(parameter=parameter), test_data_value)
                test_data_value += 1
                data_value.update_int(test_data_value)
                g.copy_to_next_round(data_value)
            e.advance_to_next_round()

    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.create_group(max_size=10, experiment=self.experiment)
        count = 0
        logger.debug(
            "self participants: %s (%s)", self.participants, len(self.participants))
        for p in self.participants:
            pgr = g.add_participant(p)
            g = pgr.group
            count += 1
            if count > 10:
                count %= 10
            self.assertEqual(g.participant_set.count(), count,
                             "group.participant_set count should be %i" % count)
            self.assertEqual(g.size, count, "group size should be %i" % count)


class ParticipantExperimentRelationshipTest(BaseVcwebTest):

    def test_send_emails(self):
        e = self.experiment.clone()
        institution = Institution.objects.get(pk=1)
        number_of_participants = 10
        emails = ['test%s@asu.edu' %
                  index for index in range(number_of_participants)]
        e.register_participants(emails=emails, institution=institution,
                                password='test')

    def test_participant_identifier(self):
        """ exercises the generation of participant_identifier """
        e = self.experiment.clone()
        for p in self.participants:
            per = ParticipantExperimentRelationship.objects.create(participant=p,
                                                                   experiment=e, created_by=self.experimenter.user)
            self.assertTrue(per.id > 0)
            logger.debug("Participant identifier is %s - sequential id is %i", per.participant_identifier,
                         per.sequential_participant_identifier)
            self.assertTrue(per.participant_identifier)
            self.assertTrue(per.sequential_participant_identifier > 0)

        self.assertEqual(e.participant_set.count(), self.participants.count())


class RoundConfigurationTest(BaseVcwebTest):

    def test_repeating_round(self):
        self.advance_to_data_round()
        e = self.experiment
        current_round = e.current_round
        current_round.repeat = 5
        current_round.save()
        sn = e.current_round_sequence_number
        csn = e.current_repeated_round_sequence_number
        rd0 = e.current_round_data
        self.assertEqual(csn, 0)
        for i in range(1, 5):
            e.advance_to_next_round()
            self.assertEqual(e.current_round_sequence_number, sn)
            logger.debug(
                "current repeating round: %s", e.current_repeated_round_sequence_number)
            self.assertEqual(e.current_repeated_round_sequence_number, i)
            self.assertNotEqual(rd0, e.current_round_data)
        ''' FIXME: doesn't currently work with round configuration setup
        e.advance_to_next_round()
        logger.debug("current repeating round: %s", e.current_repeated_round_sequence_number)
        self.assertEqual(e.current_round_sequence_number, sn + 1)
        self.assertEqual(e.current_repeated_round_sequence_number, 0)
        '''

    def test_round_parameters(self):
        e = self.experiment
        p = self.create_parameter(scope='round', name='test_round_parameter', parameter_type='int')
        self.assertTrue(p.pk > 0)
        self.assertEqual(p.value_field_name, 'int_value')

        for val in (14, '14', 14.0, '14.0'):
            rp = RoundParameterValue.objects.create(
                parameter=p, round_configuration=e.current_round, value=val)
            self.assertTrue(rp.pk > 0)
            self.assertEqual(rp.value, 14)
            self.assertEqual(rp.int_value, 14)

        # Parameter.type generates the value_field_name property by concatenating the name of the type with _value
        sample_values_for_type = {
            'int': 3, 'float': 3.0, 'string': 'ich bin ein ooga booga', 'boolean': True}
        for value_type in ('int', 'float', 'string', 'boolean'):
            p = self.create_parameter(scope='round',
                                      name="test_round_parameter_%s" % value_type,
                                      parameter_type=value_type)
            self.assertTrue(p.pk > 0)
            field_name = '%s_value' % value_type
            self.assertEqual(p.value_field_name, field_name)
            rp = RoundParameterValue.objects.create(parameter=p, round_configuration=e.current_round,
                                                    value=sample_values_for_type[value_type])
            self.assertEqual(rp.value, sample_values_for_type[value_type])
            self.assertEqual(getattr(rp, field_name), sample_values_for_type[value_type])


class SubjectPoolInvitationTest(SubjectPoolTest):

    def test_invitations(self):

        self.setup_participants()
        last_week_date = datetime.now() - timedelta(days=7)

        for index in range(3):
            # First Iteration
            logger.debug("Iteration %d", index + 1)
            es_pk_list = self.setup_experiment_sessions()
            x = self.get_final_participants()
            # None left in the participant pool to invite
            if not x:
                break
            pk_list = [p.pk for p in x]

            # The chosen set of participants should not have participated
            # in past for the same experiment
            self.assertEqual(
                ParticipantSignup.objects.filter(attendance__in=[0, 3], invitation__participant__in=x).count(), 0)

            # The chosen set of participants should not have received
            # invitations in last threshold days
            self.assertEqual(Invitation.objects.filter(participant__in=x, date_created__gt=last_week_date).count(),
                             0)
            # The chosen set of participants should be from provided
            # university and must have enabled can_receive invitations
            self.assertEqual(
                Participant.objects.filter(can_receive_invitations=True,
                                           institution__name='Arizona State University',
                                           pk__in=pk_list).count(), len(x))

            self.setup_invitations(x, es_pk_list)

            self.setup_participant_signup(x, es_pk_list)


class ParameterizedValueMixinTest(BaseVcwebTest):

    def test_invalid_parameters(self):
        e = self.experiment
        e.activate()
        cr = e.current_round
        dpv = None
        try:
            dpv = cr.get_parameter_value(default=23)
            self.fail("should have raised a ValueError")
        except ValueError:
            self.assertIsNone(dpv)

    def test_default_value(self):
        dpv = DefaultValue(23)
        self.assertEqual(dpv.value, 23)
        self.assertEqual(dpv.int_value, 23)
        self.assertEqual(dpv.anything, 23)
        self.assertEqual(str(dpv), '23')
        self.assertEqual(unicode(dpv), u'23')

    def test_set_parameter_value(self):
        e = self.experiment
        e.activate()
        cr = e.current_round
        pv = None
        try:
            pv = cr.set_parameter_value(name='nonexistent_parameter')
            self.fail("parameter value with nonexistent parameter should not be able to be set")
        except Parameter.DoesNotExist:
            self.assertIsNone(pv)
        parameter = self.create_parameter(name='existent_parameter', scope=Parameter.Scope.ROUND, parameter_type='int')
        pv = cr.set_parameter_value(parameter=parameter, value=17)
        self.assertIsNotNone(pv)
        self.assertFalse(type(pv) is DefaultValue)
        self.assertEqual(pv.int_value, 17)

    def test_get_parameter_value(self):
        e = self.experiment
        e.activate()
        cr = e.current_round
        pv = None
        try:
            pv = cr.get_parameter_value(name='nonexistent_parameter')
            self.fail("parameter value with nonexistent parameter should not be able to be retrieved")
        except Parameter.DoesNotExist:
            self.assertIsNone(pv)
        parameter = self.create_parameter(name='existent_parameter', scope=Parameter.Scope.ROUND, parameter_type='int')
        pv = cr.get_parameter_value(parameter=parameter, default=17)
        self.assertIsNotNone(pv)
        self.assertFalse(type(pv) is DefaultValue)
        self.assertEqual(pv.int_value, 17)


class DataValueMixinTest(BaseVcwebTest):

    def test_set_data_value(self):
        e = self.experiment
        e.activate()
        parameter = self.create_parameter(scope=Parameter.Scope.GROUP, name='test_data_value_parameter')
        expected_test_value = 'test value'
        for g in e.groups:
            dv = None
            try:
                dv = g.set_data_value(parameter_name='nonexistent_parameter', value=expected_test_value)
                self.fail('data value with nonexistent parameter should not be able to be set')
            except Parameter.DoesNotExist:
                self.assertIsNone(dv)
            dv = g.set_data_value(parameter=parameter, value=expected_test_value)
            self.assertIsNotNone(dv)
            self.assertFalse(type(dv) is DefaultValue)
            self.assertEqual(dv.string_value, expected_test_value)

    def test_get_data_value(self):
        e = self.experiment
        e.activate()
        parameter = self.create_parameter(scope=Parameter.Scope.GROUP, name='test_data_value_parameter')
        expected_test_value = 'test value'
        for g in e.groups:
            dv = None
            try:
                dv = g.get_data_value(name='nonexistent_parameter')
                self.fail('data value with nonexistent parameter should not be able to be retrieved')
            except Parameter.DoesNotExist:
                self.assertIsNone(dv)
            dv = g.get_data_value(parameter=parameter, default=expected_test_value)
            self.assertIsNotNone(dv)
            self.assertFalse(type(dv) is DefaultValue)
            self.assertEqual(dv.string_value, expected_test_value)


class GraphDatabaseTest(BaseVcwebTest):

    def test_graph_database_init_and_shutdown(self):
        from ..graph import get_graph_db, shutdown, VcwebGraphDatabase
        db = get_graph_db()
        for i in range(1, 10):
            self.assertEqual(db, get_graph_db())
        shutdown()
        self.assertIsNone(VcwebGraphDatabase._db)
        db = get_graph_db()
        for i in range(1, 10):
            self.assertEqual(db, get_graph_db())
        shutdown()


class BookmarkedExperimentMetadataTest(BaseVcwebTest):

    def test_bookmarks(self):
        e = self.demo_experimenter
        bookmarks = ExperimentMetadata.objects.bookmarked(e)
        forestry = ExperimentMetadata.objects.get(namespace='forestry')
        bound = ExperimentMetadata.objects.get(namespace='bound')
        lighterprints = ExperimentMetadata.objects.get(namespace='lighterprints')
        self.assertEqual(ExperimentMetadata.objects.count(), bookmarks.count())
        for experiment_metadata in bookmarks:
            self.assertFalse(experiment_metadata.bookmarked)
        BookmarkedExperimentMetadata.objects.create(experiment_metadata=forestry, experimenter=e)
        BookmarkedExperimentMetadata.objects.create(experiment_metadata=bound, experimenter=e)
        bookmarks = ExperimentMetadata.objects.bookmarked(e)
        self.assertEqual(ExperimentMetadata.objects.count(), bookmarks.count())
        for em in bookmarks:
            self.assertEquals(em.bookmarked, em in (forestry, bound))
        new_experimenter = self.create_experimenter()
        bookmarks = ExperimentMetadata.objects.bookmarked(new_experimenter)
        self.assertEqual(ExperimentMetadata.objects.count(), bookmarks.count())
        for experiment_metadata in bookmarks:
            self.assertFalse(experiment_metadata.bookmarked)
