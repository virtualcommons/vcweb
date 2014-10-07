from ..models import (Participant, ExperimentMetadata,
                      Experiment, Invitation, ParticipantSignup, PermissionGroup)
from ..forms import LoginForm
from ..views import ExperimenterDashboardViewModel
from .common import BaseVcwebTest, SubjectPoolTest
from django.core.urlresolvers import reverse

import random
import json
import logging


logger = logging.getLogger(__name__)


class AuthTest(BaseVcwebTest):

    def test_authentication_redirect(self):
        experiment = self.experiment
        response = self.get(self.login_url)
        self.assertEqual(200, response.status_code)
        self.assertTrue(self.login(username=experiment.experimenter.email,
                                   password=BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD))
        response = self.get(self.login_url)
        self.assertEqual(302, response.status_code)

    def test_invalid_password(self):
        experiment = self.experiment
        self.assertFalse(
            self.login(username=experiment.experimenter.email, password='jibber jabber'))
        response = self.post(self.login_url, {'email': experiment.experimenter.email,
                                              'password': 'jibber jabber'})
        self.assertTrue(
            LoginForm.INVALID_AUTHENTICATION_MESSAGE in response.content)

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
            self.assertTrue(p.should_update_profile)
            self.assertTrue(self.login_participant(p))
            self.assertFalse(p.is_demo_participant)
            self.assertTrue(p.user.groups.filter(name='Participants').exists())
            response = self.get(self.dashboard_url)
            self.assertEqual(302, response.status_code)
            self.assertTrue(self.profile_url in response['Location'])
# FIXME: fill in profile save
            self.post(self.profile_url, {})


class ParticipantDashboardTest(BaseVcwebTest):

    def test_demo_participants_dashboard(self):
        e = self.experiment
        e.activate()
        for p in e.participant_set.all():
            self.assertFalse(p.should_update_profile)
            self.assertTrue(self.login_participant(p))
            self.assertTrue(p.is_demo_participant)
            response = self.get(self.dashboard_url)
# test demo participants don't need to get redirected to the account profile to fill out profile info when they visit
# the dashboard.
            self.assertEqual(200, response.status_code)

    def test_completed_profile_dashboard(self):
        e = self.experiment
        e.activate()
        participant_group = PermissionGroup.participant.get_django_group()
        for p in e.participant_set.all():
            self.assertFalse(p.should_update_profile)
            p.can_receive_invitations = True
            p.user.groups = [participant_group]
            p.user.save()
            self.assertTrue(p.should_update_profile)
            p.class_status = 'Freshman'
            p.gender = 'F'
            p.favorite_sport = 'Football'
            p.favorite_color = 'pink'
            p.favorite_food = 'Other'
            p.favorite_movie_genre = 'Documentary'
            p.major = 'Science'
            p.save()
            self.assertFalse(p.should_update_profile)
            self.assertTrue(self.login_participant(p))
            response = self.get(self.dashboard_url)
            self.assertEqual(200, response.status_code)


class ExperimenterDashboardTest(BaseVcwebTest):

    def test_dashboard_view_model(self):
        dashboard_view_model = ExperimenterDashboardViewModel(
            self.demo_experimenter.user)
        vmdict = dashboard_view_model.to_dict()
        self.assertFalse(vmdict['isAdmin'])
        self.assertEqual(vmdict['experimenterId'], self.demo_experimenter.pk)
        self.assertFalse(vmdict['runningExperiments'])
        self.experiment.activate()
        dashboard_view_model = ExperimenterDashboardViewModel(
            self.experiment.experimenter.user)
        vmdict = dashboard_view_model.to_dict()
        self.assertFalse(vmdict['isAdmin'])
        self.assertEqual(
            vmdict['experimenterId'], self.experiment.experimenter.pk)
        self.assertTrue(vmdict['runningExperiments'])
        self.assertEqual(
            self.experiment.status, vmdict['runningExperiments'][0]['status'])

    def test_experimenter_dashboard(self):
        e = self.experiment
        e.activate()
        experimenter = e.experimenter
        self.assertTrue(self.login_experimenter(experimenter))
        self.assertTrue(experimenter.approved)
        self.assertTrue(experimenter.is_demo_experimenter)
        response = self.get(self.dashboard_url)
        self.assertEqual(200, response.status_code)


class ClearParticipantsApiTest(BaseVcwebTest):

    def test_api(self):
        self.login_experimenter()
        e = self.experiment
        e.activate()
        self.assertTrue(e.participant_set.count() > 0)
        response = self.post(self.update_experiment_url,
                             {'experiment_id': self.experiment.pk, 'action': 'clear'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(e.participant_set.count(), 0)

    def test_unauthorized_experimenter_access(self):
        new_experimenter = self.create_experimenter()
        self.login_experimenter(new_experimenter)
        response = self.post(self.update_experiment_url,
                             {'experiment_id': self.experiment.pk, 'action': 'clear'})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.experiment.participant_set.count() > 0)

    def test_unauthorized_participant_access(self):
        self.login_participant(self.experiment.participant_set.first())
        response = self.post(self.update_experiment_url,
                             {'experiment_id': self.experiment.pk, 'action': 'clear'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.experiment.participant_set.count() > 0)


class ActivateApiTest(BaseVcwebTest):

    def test_activate(self):
        self.assertFalse(self.experiment.is_active)
        self.login_experimenter()
        response = self.post(self.update_experiment_url,
                             {'experiment_id': self.experiment.pk, 'action': 'activate'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.experiment.is_active)
        self.assertEqual(len(self.participant_group_relationships),
                         self.experiment.experiment_configuration.max_group_size * len(self.experiment.groups))
        response = self.post(self.update_experiment_url,
                             {'experiment_id': self.experiment.pk, 'action': 'deactivate'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.experiment.is_active)


class ArchiveApiTest(BaseVcwebTest):

    def test_archive(self):
        self.login_experimenter()
        self.experiment.activate()
        self.assertFalse(self.experiment.is_archived)
        response = self.post(self.update_experiment_url,
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
        response = self.post(reverse('core:clone_experiment'),
                             {'experiment_id': self.experiment.pk,
                              'action': 'clone'})
        experiment_json = json.loads(response.content)
        cloned_experiment = Experiment.objects.get(
            pk=experiment_json['experiment']['pk'])
        self.assertEqual(
            cloned_experiment.experiment_metadata, self.experiment.experiment_metadata)
        self.assertEqual(
            cloned_experiment.experiment_configuration, self.experiment.experiment_configuration)
        self.assertNotEqual(
            cloned_experiment.experimenter, self.experiment.experimenter)
        self.assertEqual(cloned_experiment.experimenter, experimenter)


class CheckEmailTest(BaseVcwebTest):

    def test_email_available(self):
        self.experiment.activate()
        for p in self.participants:
            response = self.get(self.check_email_url, {'email': p.email})
            self.assertEqual(response.status_code, 200)


class SubjectPoolViewTest(SubjectPoolTest):

    def test_subjectpool_experimenter_page(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        response = self.get(reverse('subjectpool:experimenter_index'))
        self.assertEqual(200, response.status_code)

    def test_send_invitations(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        self.setup_participants()
        es_pk_list = self.setup_experiment_sessions()

        response = self.post(reverse('subjectpool:send_invites'),
                             {'number_of_people': 30, 'only_undergrad': 'on',
                              'affiliated_institution': 'Arizona State University',
                              'invitation_subject': 'Test', 'invitation_text': 'Testing',
                              'session_pk_list': str(es_pk_list[0])})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)

        self.assertTrue(response_dict['success'])

    def test_get_session_events(self):
        fro = 1409554800000
        to = 1412146800000
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        response = self.get(
            '/subject-pool/session/events?from=' + str(fro) + '&to=' + str(to) + '/')
        self.assertEqual(200, response.status_code)

    def test_manage_experiment_session(self):
        # test creating, deleting and updating  experiment session
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        # test create experiment session
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(reverse('subjectpool:manage_experiment_session'),
                             {'pk': -1, 'experiment_metadata_pk': em.pk,
                              'start_date': '2014-09-23', 'start_hour': 2,
                              'start_min': 0, 'capacity': 10, 'location': 'Online',
                              'end_date': '2014-09-23', 'end_hour': 3, 'end_min': 0,
                              'request_type': 'create'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test edit/update experiment session
        response = self.post(reverse('subjectpool:manage_experiment_session'),
                             {'pk': response_dict['session']['pk'],
                              'experiment_metadata_pk': em.pk,
                              'start_date': '2014-09-23', 'start_hour': 2,
                              'start_min': 0, 'capacity': 10, 'location': 'Online',
                              'end_date': '2014-09-23', 'end_hour': 4,
                              'end_min': 0, 'request_type': 'update'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test delete experiment session
        response = self.post(reverse('subjectpool:manage_experiment_session'),
                             {'pk': response_dict['session']['pk'], 'request_type': 'delete'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

    def test_experiment_session_signup_page(self):

        self.setup_participants()
        es_pk_list = self.setup_experiment_sessions()
        x = self.get_final_participants()

        pk_list = [p.pk for p in x]
        participant = Participant.objects.get(pk=random.choice(pk_list))
        self.assertTrue(self.login_participant(participant))

        response = self.get(reverse('subjectpool:experiment_session_signup'))
        self.assertEqual(200, response.status_code)

        self.setup_invitations(x, es_pk_list)
        invitation = Invitation.objects.filter(participant=participant).order_by('?')[0]

        response = self.post(reverse('subjectpool:submit_experiment_session_signup'), {
            'invitation_pk': invitation.pk,
            'experiment_metadata_pk': invitation.experiment_session.experiment_metadata_id
        })

        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # test cancel session signup
        ps = ParticipantSignup.objects.get(invitation=invitation)
        response = self.post(reverse('subjectpool:cancel_experiment_session_signup'), {'pk': ps.pk})
        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # test canceling an already cancel session signup
        response = self.post(reverse('subjectpool:cancel_experiment_session_signup'), {'pk': ps.pk})
        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # Test submit experiment session signup on zero capacity
        invitation.experiment_session.capacity = 0
        invitation.experiment_session.save()

        response = self.post(reverse('subjectpool:submit_experiment_session_signup'), {
            'invitation_pk': invitation.pk,
            'experiment_metadata_pk': invitation.experiment_session.experiment_metadata.pk
        })
        self.assertEqual(302, response.status_code)
        self.assertTrue(reverse('core:dashboard') in response['Location'])
        ps = ParticipantSignup.objects.waitlist(experiment_session_pk=invitation.experiment_session_id)
        self.assertTrue(ps.exists())
        self.assertEqual(ps[0].invitation, invitation)
