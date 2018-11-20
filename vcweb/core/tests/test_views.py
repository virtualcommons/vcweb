import json
import logging
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from .common import BaseVcwebTest, SubjectPoolTest
from ..models import (Participant, ExperimentMetadata, ExperimentSession, Invitation, ParticipantSignup,
                      PermissionGroup, BookmarkedExperimentMetadata)
from ..views import (DashboardViewModel, ExperimenterDashboardViewModel)

logger = logging.getLogger(__name__)


class AuthTest(BaseVcwebTest):

    INVALID_LOGIN_MESSAGE = str(AuthenticationForm.error_messages['invalid_login'])
    INACTIVE_USER_MESSAGE = str(AuthenticationForm.error_messages['inactive'])

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
        self.assertFalse(self.login(username=experiment.experimenter.email, password='jibber jabber'))
        response = self.post(self.login_url, {'email': experiment.experimenter.email,
                                              'password': 'jibber jabber'})
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_inactive_user_login(self):
        User = get_user_model()
        user = User.objects.first()
        user.is_active = False
        user.save()
        response = self.post(self.login_url, {'email': user.email, 'password': 'test'})
        self.assertFalse(response.wsgi_request.user.is_authenticated)

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

    def test_update_profile(self):
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


class ParticipateTest(BaseVcwebTest):

    def test_demo_participant(self):
        e = self.experiment
        e.activate()
        for p in e.participant_set.all():
            self.assertTrue(self.login_participant(p))
            response = self.get('core:participate')
            # should redirect to first active experiment participant url
            self.assertEqual(302, response.status_code)
            self.assertTrue(e.participant_url in response['Location'])


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
        dashboard_view_model = DashboardViewModel.create(self.demo_experimenter.user)
        self.assertEqual(type(dashboard_view_model), ExperimenterDashboardViewModel)
        vmdict = dashboard_view_model.to_dict()
        self.assertFalse(vmdict['isAdmin'])
        self.assertEqual(vmdict['experimenterId'], self.demo_experimenter.pk)
        self.assertFalse(vmdict['runningExperiments'])
        self.experiment.activate()
        dashboard_view_model = DashboardViewModel.create(self.experiment.experimenter.user)
        vmdict = dashboard_view_model.to_dict()
        self.assertFalse(vmdict['isAdmin'])
        self.assertEqual(vmdict['experimenterId'], self.experiment.experimenter.pk)
        self.assertTrue(vmdict['runningExperiments'])
        self.assertEqual(self.experiment.status, vmdict['runningExperiments'][0]['status'])

    def test_experimenter_dashboard(self):
        e = self.experiment
        e.activate()
        experimenter = e.experimenter
        self.assertTrue(self.login_experimenter(experimenter))
        self.assertTrue(experimenter.approved)
        self.assertTrue(experimenter.is_demo_experimenter)
        response = self.get(self.dashboard_url)
        self.assertEqual(200, response.status_code)


class BookmarkExperimentMetadataTest(BaseVcwebTest):

    def test_toggle_bookmark(self):
        experimenter = self.experimenter
        experiment = self.experiment
        self.assertTrue(self.login_experimenter(experimenter))
        self.assertFalse(BookmarkedExperimentMetadata.objects.filter(experimenter=experimenter).exists())
        response = self.post('core:bookmark_experiment_metadata', {
            'experimenter_id': experimenter.pk,
            'experiment_metadata_id': experiment.experiment_metadata.pk,
        })
        self.assertEqual(200, response.status_code)
        self.assertTrue(BookmarkedExperimentMetadata.objects.filter(experimenter=experimenter).exists())
        response = self.post('core:bookmark_experiment_metadata', {
            'experimenter_id': experimenter.pk,
            'experiment_metadata_id': experiment.experiment_metadata.pk,
        })
        self.assertEqual(200, response.status_code)
        self.assertFalse(BookmarkedExperimentMetadata.objects.filter(experimenter=experimenter).exists())


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
        self.assertEqual(response.status_code, 404)
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

        response = self.get(self.reverse('subjectpool:subjectpool_index'))
        self.assertEqual(200, response.status_code)

    def test_send_invitations(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        # Test Invalid form
        response = self.post(self.reverse('subjectpool:send_invites'),
                             {'number_of_people': 30, 'only_undergrad': 'on'})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)

        self.assertFalse(response_dict['success'])

        es_pk_list = self.setup_experiment_sessions()

        # Test with experiment sessions from from more than one experiment metadata
        response = self.post(self.reverse('subjectpool:send_invites'), {
            'number_of_people': 30,
            'only_undergrad': 'on', 'affiliated_institution': self.get_default_institution().pk, 'invitation_subject': 'Test',
            'invitation_text': 'Testing', 'gender': 'M', 'session_pk_list': "-1"})
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertFalse(response_dict['success'])

        # Test without participants
        response = self.post(self.reverse('subjectpool:send_invites'), {
            'number_of_people': 30,
            'only_undergrad': 'on', 'gender': 'M', 'affiliated_institution': self.get_default_institution().pk,
            'invitation_subject': 'Test', 'invitation_text': 'Testing', 'session_pk_list': str(es_pk_list[0])})
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # Test with participants
        self.setup_participants()

        response = self.post(self.reverse('subjectpool:send_invites'), {
            'number_of_people': 30,
            'only_undergrad': 'on', 'gender': 'A', 'affiliated_institution': self.get_default_institution().pk,
            'invitation_subject': 'Test', 'invitation_text': 'Testing', 'session_pk_list': str(es_pk_list[0])})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)

        self.assertTrue(response_dict['success'])

    def test_get_session_events(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(self.reverse('subjectpool:manage_experiment_session', args=[-1]), {
            'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
            'location': 'Online', 'scheduled_end_date': '2014-09-23 3:0', 'waitlist': True})
        response_dict = json.loads(response.content)
        # FIXME: make assertions on response_dict..
        fro = 1411000000000
        to = 1411500000000
        response = self.get('/subject-pool/session/events?from=' + str(fro) + '&to=' + str(to) + '/')
        self.assertEqual(200, response.status_code)

    def test_downloading_experiment_session_data(self):
        # test downloading experiment session data
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(self.reverse('subjectpool:manage_experiment_session', args=[-1]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 3:0', 'waitlist': False})
        response_dict = json.loads(response.content)
        es = ExperimentSession.objects.get(pk=response_dict['session']['pk'])
        es.creator = e.user
        es.save()
        response = self.get('/subject-pool/session/' + str(es.pk) + '/download/')
        self.assertEqual(200, response.status_code)

    def test_manage_experiment_session(self):
        # test creating, deleting and updating  experiment session
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))

        # test create experiment session
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(self.reverse('subjectpool:manage_experiment_session', args=[-1]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 3:0', 'waitlist': True})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test edit/update experiment session
        response = self.post(self.reverse('subjectpool:manage_experiment_session',
                                          args=[response_dict['session']['pk']]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 4:0', 'waitlist': True})
        self.assertEqual(200, response.status_code)

        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test incomplete form
        response = self.post(self.reverse('subjectpool:manage_experiment_session',
                                          args=[response_dict['session']['pk']]),
                             {'experiment_metadata': em.pk, 'request_type': 'delete'})
        self.assertEqual(200, response.status_code)

        response = json.loads(response.content)
        self.assertFalse(response['success'])

        # test delete experiment session
        response = self.post(self.reverse('subjectpool:manage_experiment_session',
                                          args=[response_dict['session']['pk']]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 4:0', 'request_type': 'delete',
                              'waitlist': True})
        self.assertEqual(200, response.status_code)

        response = json.loads(response.content)
        self.assertTrue(response_dict['success'])

    def test_experiment_session_signup_page(self):
        self.setup_participants()
        es_pk_list = self.setup_experiment_sessions()
        x = self.get_final_participants()

        pk_list = [p.pk for p in x]
        participant = Participant.objects.get(pk=random.choice(pk_list))
        self.assertTrue(self.login_participant(participant))

        response = self.get(self.reverse('subjectpool:experiment_session_signup'))
        self.assertEqual(200, response.status_code)

        self.setup_invitations(x, es_pk_list)
        invitation = Invitation.objects.filter(participant=participant).order_by('?')[0]

        response = self.post(self.reverse('subjectpool:submit_experiment_session_signup'), {
            'invitation_pk': invitation.pk,
            'experiment_metadata_pk': invitation.experiment_session.experiment_metadata_id
        })

        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # test cancel session signup
        ps = ParticipantSignup.objects.get(invitation=invitation)
        response = self.post(self.reverse('subjectpool:cancel_experiment_session_signup'), {'pk': ps.pk})
        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # test canceling an already canceled session signup
        response = self.post(self.reverse('subjectpool:cancel_experiment_session_signup'), {'pk': ps.pk})
        self.assertEqual(302, response.status_code)
        self.assertTrue(self.dashboard_url in response['Location'])

        # Test submit experiment session signup on zero capacity
        # zero capacity experiment sessions shouldn't have any waitlist
        invitation.experiment_session.capacity = 0
        invitation.experiment_session.save()

        response = self.post(self.reverse('subjectpool:submit_experiment_session_signup'), {
            'invitation_pk': invitation.pk,
            'experiment_metadata_pk': invitation.experiment_session.experiment_metadata.pk
        })
        self.assertEqual(302, response.status_code)
        ps = ParticipantSignup.objects.waitlist(experiment_session_pk=invitation.experiment_session_id)
        self.assertFalse(ps.exists())

    def test_manage_participant_attendance(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(self.reverse('subjectpool:manage_experiment_session', args=[-1]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 3:0', 'waitlist': True})
        response_dict = json.loads(response.content)

        es = ExperimentSession.objects.get(pk=response_dict['session']['pk'])
        es.creator = e.user
        es.save()

        response = self.get(self.reverse('subjectpool:session_event_detail', args=[es.pk]))
        self.assertEqual(200, response.status_code)

    def test_invitation_count(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))
        self.setup_participants()
        es_pk_list = self.setup_experiment_sessions()
        response = self.post(self.reverse('subjectpool:get_invitations_count'), {
            'session_pk_list': ",".join(map(str, es_pk_list)),
            'number_of_people': 30,
            'only_undergrad': 'on',
            'gender': 'M',
            'affiliated_institution': self.get_default_institution().pk,
            'invitation_subject': 'Text',
            'invitation_text': 'Text'
        })
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])

        # test invalid experiment sessions
        response = self.post(self.reverse('subjectpool:get_invitations_count'), {
            'session_pk_list': -1,
            'affiliated_institution': self.get_default_institution().pk,
            'only_undergrad': True,
            'invitation_text': 'Test',
            'invitation_subject': 'Test',
            'gender': 'M',
            'number_of_people': 30})
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertFalse(response_dict['success'])

    def test_invitation_email_preview(self):
        e = self.create_experimenter()
        self.assertTrue(self.login_experimenter(e))
        em = ExperimentMetadata.objects.order_by('?')[0]
        response = self.post(self.reverse('subjectpool:manage_experiment_session', args=[-1]),
                             {'experiment_metadata': em.pk, 'scheduled_date': '2014-09-23 2:0', 'capacity': 10,
                              'location': 'Online', 'scheduled_end_date': '2014-09-23 3:0', 'waitlist': True})
        response_dict_session = json.loads(response.content)

        # Test invalid form
        response = self.post(self.reverse('subjectpool:invite_email_preview'),
                             {'invitation_subject': 'Test', 'invitation_text': 'Test'})
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertFalse(response_dict['success'])

        # Test valid form
        response = self.post(self.reverse('subjectpool:invite_email_preview'), {
            'number_of_people': 30, 'only_undergrad': 'on',
            'gender': 'M', 'affiliated_institution': self.get_default_institution().pk,
            'invitation_subject': 'Text', 'invitation_text': 'Text',
            'session_pk_list': response_dict_session['session']['pk']})
        self.assertEqual(200, response.status_code)
        response_dict = json.loads(response.content)
        self.assertTrue(response_dict['success'])
