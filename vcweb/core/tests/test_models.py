from datetime import datetime, timedelta, date
import random
import logging

from django.contrib.auth.models import User
from django.core import serializers

from .common import BaseVcwebTest
from .. import signals
from ..models import (ParticipantRoundDataValue, Participant, ParticipantExperimentRelationship,
                      ParticipantGroupRelationship, ExperimentMetadata, Parameter, RoundParameterValue, Institution,
                      ExperimentSession, Invitation, ParticipantSignup, DefaultValue)
from ..subjectpool.views import get_potential_participants

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

    def test_start_round(self):
        signals.round_started.connect(
            self.round_started_test_handler, sender=self)
        self.experiment.start_round(sender=self)
        self.assertTrue(self.experiment.is_active)
        self.assertFalse(self.experiment.start_round(
            sender=self), "subsequent start rounds should be no-ops and return false")

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
        experiment = self.experiment
        experiment.activate()
        self.assertEqual(0, experiment.current_round_elapsed_time.seconds)
        # FIXME: exercise current_round_elapsed_time and total_elapsed_time

    def test_playable_round(self):
        # advance_to_next_round automatically starts the round
        e = self.advance_to_data_round()
        current_round_data = e.current_round_data
        logger.debug("current round data: %s", current_round_data)
        e.end_round()
        for group in e.groups:
            for parameter in group.parameters.all():
                gdvs = current_round_data.group_data_value_set.filter(
                    parameter=parameter, group=group)
                self.assertEqual(
                    1, gdvs.count(), "Should only be a single group data value")
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


class InvitationAlgorithmTest(BaseVcwebTest):

    def set_up_participants(self):
        password = "test"
        participants = []
        for x in xrange(500):
            email = "student" + str(x) + "asu@asu.edu"
            user = User.objects.create_user(first_name='xyz', last_name='%d' % x, username=email, email=email,
                                            password=password)
            user.save()
            p = Participant(user=user)
            p.can_receive_invitations = random.choice([True, False])
            p.gender = random.choice(['M', 'F'])
            year = random.choice(range(1980, 1995))
            month = random.choice(range(1, 12))
            day = random.choice(range(1, 28))
            random_date = datetime(year, month, day)
            p.birthdate = random_date
            p.major = 'CS'
            p.class_status = random.choice(
                ['Freshman', 'Sophomore', 'Junior', 'Senior'])
            p.institution = Institution.objects.get(
                name="Arizona State University")
            participants.append(p)
        Participant.objects.bulk_create(participants)
        # logger.debug("TOTAL PARTICIPANTS %d", len(Participant.objects.all()))

    def set_up_experiment_sessions(self):
        e = self.experiment
        es_pk = []
        for x in xrange(4):
            es = ExperimentSession()
            es.experiment_metadata = e.experiment_metadata
            year = date.today().year
            month = date.today().month
            day = random.choice(range(1, 30))
            random_date = datetime(year, month, day)
            es.scheduled_date = random_date
            es.scheduled_end_date = random_date
            es.capacity = 1
            es.location = "Online"
            es.creator = User.objects.get(pk=256)  # creator is vcweb
            es.date_created = datetime.now()
            es.save()
            es_pk.append(es.pk)
        return es_pk

    def get_final_participants(self):
        potential_participants = get_potential_participants(
            self.experiment_metadata.pk, "Arizona State University")
        potential_participants_count = len(potential_participants)
        # logger.debug(potential_participants)
        no_of_invitations = 50

        if potential_participants_count == 0:
            final_participants = []
        else:
            if potential_participants_count < no_of_invitations:
                final_participants = potential_participants
            else:
                priority_list = ParticipantSignup.objects \
                    .filter(invitation__participant__in=potential_participants,
                            attendance=ParticipantSignup.ATTENDANCE.discharged) \
                    .values_list('invitation__participant__pk', flat=True)
                priority_list = Participant.objects.filter(
                    pk__in=priority_list)
                logger.debug("Priority Participants")
                logger.debug(priority_list)
                if len(priority_list) >= no_of_invitations:
                    final_participants = random.sample(
                        priority_list, no_of_invitations)
                else:
                    final_participants = list(priority_list)
                    # logger.debug(final_participants)
                    new_potential_participants = list(
                        set(potential_participants) - set(priority_list))
                    # logger.debug("New Potential Participants")
                    # logger.debug(new_potential_participants)
                    x = random.sample(
                        new_potential_participants, no_of_invitations - len(priority_list))
                    # logger.debug("Random Sample")
                    # logger.debug(x)
                    final_participants += x
                    # logger.debug("Final Participants")
                    # logger.debug(final_participants)
        return final_participants

    def set_up_participant_signup(self, participant_list, es_pk_list):
        participant_list = participant_list[:25]

        for person in participant_list:
            inv = Invitation.objects.filter(
                participant=person, experiment_session__pk__in=es_pk_list).order_by('?')[:1]
            ps = ParticipantSignup()
            ps.invitation = inv[0]
            year = date.today().year
            month = date.today().month - 1
            day = random.choice(range(1, 30))
            random_date = datetime(year, month, day)
            ps.date_created = random_date
            # logger.debug(random_date)
            ps.attendance = random.choice([0, 1, 2, 3])
            # logger.debug(ps.attendance)
            ps.save()

    def set_up_inv(self, participants, es_pk_list):
        invitations = []
        experiment_sessions = ExperimentSession.objects.filter(pk__in=es_pk_list)
        user = User.objects.get(pk=256)

        for participant in participants:
            # recipient_list.append(participant.email)
            for es in experiment_sessions:
                year = date.today().year
                month = date.today().month - 1
                day = random.choice(range(1, 30))
                random_date = datetime(year, month, day)
                invitations.append(Invitation(participant=participant, experiment_session=es, date_created=random_date,
                                              sender=user))

        Invitation.objects.bulk_create(invitations)

    def test_invitations(self):

        self.set_up_participants()

        last_week_date = datetime.now() - timedelta(days=7)

        for index in range(3):
            # First Iteration
            logger.debug("Iteration %d", index + 1)

            es_pk_list = self.set_up_experiment_sessions()

            x = self.get_final_participants()

            if x:
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

                self.set_up_inv(x, es_pk_list)

                self.set_up_participant_signup(x, es_pk_list)
            else:
                break


class ParameterizedValueMixinTest(BaseVcwebTest):

    def test_get_default_value(self):
        e = self.experiment
        e.activate()
        cr = e.current_round
        dpv = cr.get_parameter_value(default=23)
        self.assertIsNotNone(dpv)
        self.assertEqual(type(dpv), DefaultValue)
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
