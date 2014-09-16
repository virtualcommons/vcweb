from ..models import ExperimentMetadata, Experiment, ExperimentSession
from .common import BaseVcwebTest, SubjectPoolTest

import json
import logging

logger = logging.getLogger(__name__)


class AuthTest(BaseVcwebTest):

    def test_authentication_redirect(self):
        experiment = self.experiment
        response = self.get('/accounts/login/')
        self.assertEqual(200, response.status_code)
        self.assertTrue(self.login(username=experiment.experimenter.email,
                                   password=BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD))
        response = self.get('/accounts/login/')
        self.assertEqual(302, response.status_code)

    def test_invalid_password(self):
        experiment = self.experiment
        self.assertFalse(self.login(username=experiment.experimenter.email, password='jibber jabber'))
        response = self.post('/accounts/login', dict(username=experiment.experimenter.email,
                                                     password='jibber jabber'))
        self.assertTrue('/accounts/login' in response['Location'])

    def test_experimenter_permissions(self):
        self.assertTrue(self.login_experimenter())
        # FIXME: more tests

    def test_participant_permissions(self):
        for pgr in self.participant_group_relationships:
            self.assertTrue(self.login_participant(pgr.participant))
            # FIXME: more tests on participant permissions


class ParticipantProfileTest(BaseVcwebTest):

    def setUp(self, **kwargs):
        super(ParticipantProfileTest, self).setUp(demo_participants=False)

    def test_save_profile(self):
        e = self.experiment
        e.activate()
        for p in e.participant_set.all():
            self.assertFalse(p.is_profile_complete)
            self.assertTrue(self.login_participant(p))
            self.assertFalse(p.user.groups.filter(name='Demo Participants').exists())
            self.assertTrue(p.user.groups.filter(name='Participants').exists())
            response = self.get('/dashboard/')
            self.assertEqual(302, response.status_code)
            self.assertTrue('/accounts/profile' in response['Location'])
            self.post('/accounts/profile', {})


class ParticipantDashboardTest(BaseVcwebTest):

    def test_demo_participants_dashboard(self):
        e = self.experiment
        e.activate()
        for p in e.participant_set.all():
            self.assertFalse(p.is_profile_complete)
            self.assertTrue(self.login_participant(p))
            self.assertTrue(p.user.groups.filter(name='Demo Participants').exists())
            response = self.get('/dashboard/')
# test demo participants don't need to get redirected to the account profile to fill out profile info when they visit
# the dashboard.
            self.assertEqual(200, response.status_code)

    def test_completed_profile_dashboard(self):
        e = self.experiment
        e.activate()
        for p in e.participant_set.all():
            self.assertFalse(p.is_profile_complete)
            p.can_receive_invitations = True
            p.class_status = 'Freshman'
            p.gender = 'F'
            p.favorite_sport = 'Football'
            p.favorite_color = 'pink'
            p.favorite_food = 'Other'
            p.favorite_movie_genre = 'Documentary'
            p.major = 'Science'
            p.save()
            self.assertTrue(p.is_profile_complete)
            self.assertTrue(self.login_participant(p))
            response = self.get('/dashboard/')
            self.assertEqual(200, response.status_code)


class ClearParticipantsApiTest(BaseVcwebTest):

    def test_api(self):
        self.login_experimenter()
        e = self.experiment
        e.activate()
        self.assertTrue(e.participant_set.count() > 0)
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'clear_participants'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(e.participant_set.count(), 0)

    def test_unauthorized_experimenter_access(self):
        new_experimenter = self.create_experimenter()
        self.login_experimenter(new_experimenter)
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'clear_participants'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.experiment.participant_set.count() > 0)

    def test_unauthorized_participant_access(self):
        self.login_participant(self.experiment.participant_set.first())
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'clear_participants'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.experiment.participant_set.count() > 0)


class ActivateApiTest(BaseVcwebTest):

    def test_activate(self):
        self.assertFalse(self.experiment.is_active)
        self.login_experimenter()
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'activate'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.experiment.is_active)
        self.assertEqual(len(self.participant_group_relationships),
                         self.experiment.experiment_configuration.max_group_size * len(self.experiment.groups))
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'deactivate'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.experiment.is_active)


class ArchiveApiTest(BaseVcwebTest):

    def test_archive(self):
        self.login_experimenter()
        self.experiment.activate()
        self.assertFalse(self.experiment.is_archived)
        response = self.post('/api/experiment/update',
                             {'experiment_id': self.experiment.pk, 'action': 'archive'})
        self.assertEqual(response.status_code, 200)
        self.reload_experiment()
        self.assertTrue(self.experiment.is_archived)
        # this should be a no-op for archived experiments
        self.experiment.activate()
        self.assertTrue(self.experiment.is_archived)
        self.assertFalse(self.experiment.is_active)


class CloneExperimentTest(BaseVcwebTest):

    def test_clone(self):
        experimenter = self.create_experimenter()
        self.assertTrue(self.login_experimenter(experimenter))
        response = self.post('/api/experiment/clone',
                             {'experiment_id': self.experiment.pk})
        experiment_json = json.loads(response.content)
        cloned_experiment = Experiment.objects.get(pk=experiment_json['experiment']['pk'])
        self.assertEqual(cloned_experiment.experiment_metadata, self.experiment.experiment_metadata)
        self.assertEqual(cloned_experiment.experiment_configuration, self.experiment.experiment_configuration)
        self.assertNotEqual(cloned_experiment.experimenter, self.experiment.experimenter)
        self.assertEqual(cloned_experiment.experimenter, experimenter)


class SubjectPoolViewTest(SubjectPoolTest):

    def test_subjectpool_experimenter_page(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        response = self.get('/subject-pool/')
        self.assertEqual(200, response.status_code)

    def test_send_invitations(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        self.setup_participants()
        es_pk_list = self.setup_experiment_sessions()

        response = self.post('/subject-pool/session/invite', {'number_of_people': 30, 'only_undergrad': 'on',
                                                              'affiliated_institution': 'Arizona State University', 'invitation_subject': 'Test',
                                                              'invitation_text': 'Testing', 'session_pk_list': str(es_pk_list[0])})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)

        self.assertTrue(response_dict['success'])

    def test_get_session_events(self):
        fro = 1409554800000
        to = 1412146800000
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        response = self.get('/subject-pool/session/events?from=' + str(fro) + '&to=' + str(to) + '/')
        self.assertEqual(200, response.status_code)

    def test_update_experiment_session(self):
        # test creating, deleting and updating  experiment session
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        # test create experiment session
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post('/subject-pool/session/update', {'pk': -1, 'experiment_metadata_pk': em.pk, 'start_date': '2014-09-23',
                                                              'start_hour': 2, 'start_min': 0, 'capacity': 10, 'location': 'Online', 'end_date': '2014-09-23',
                                                              'end_hour': 3, 'end_min': 0, 'request_type': 'create'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test edit/update experiment session
        response = self.post('/subject-pool/session/update', {'pk': response_dict['session']['pk'], 'experiment_metadata_pk': em.pk,
                                                              'start_date': '2014-09-23',
                                                              'start_hour': 2, 'start_min': 0, 'capacity': 10, 'location': 'Online', 'end_date': '2014-09-23',
                                                              'end_hour': 4, 'end_min': 0, 'request_type': 'update'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test delete experiment session
        response = self.post(
            '/subject-pool/session/update', {'pk': response_dict['session']['pk'], 'request_type': 'delete'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

    def test_experiment_session_signup_page(self):
        pass
