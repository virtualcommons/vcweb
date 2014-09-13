from ..models import Experiment
from .common import BaseVcwebTest, logger
import json


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
        logger.error(response)

    def test_experimenter_permissions(self):
        self.assertTrue(self.login_experimenter())
        # FIXME: more tests

    def test_participant_permissions(self):
        for pgr in self.participant_group_relationships:
            self.assertTrue(self.login_participant(pgr.participant))
            # FIXME: more tests on participant permissions


class ParticipantDashboardTest(BaseVcwebTest):

    def test_demo_participants_dashboard(self):
        e = self.experiment
        e.activate()
        c = self.client
        for p in e.participant_set.all():
            self.assertFalse(p.is_profile_complete)
            self.assertTrue(c.login(username=p.email, password='test'))
            self.assertTrue(p.user.groups.filter(name='Demo Participants').exists())
            response = c.get('/dashboard/')
# test demo participants don't need to get redirected to the account profile to fill out profile info when they visit
# the dashboard.
            self.assertEqual(200, response.status_code)

    def test_completed_profile_dashboard(self):
        e = self.experiment
        e.activate()
        c = self.client
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
            self.assertTrue(c.login(username=p.email, password='test'))
            response = c.get('/dashboard/')
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
        self.assertEqual(response.status_code, 302)
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
        self.assertTrue(self.reload_experiment().is_archived)


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
