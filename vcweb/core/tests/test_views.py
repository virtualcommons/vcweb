from .common import BaseVcwebTest, logger


class LoginTest(BaseVcwebTest):

    def test_authentication_redirect(self):
        experiment = self.experiment
        c = self.client
        response = c.get('/accounts/login/')
        self.assertEqual(200, response.status_code)
        self.assertTrue(c.login(username=experiment.experimenter.email,
                                password=BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD))
        response = c.get('/accounts/login/')
        self.assertEqual(302, response.status_code)

    def test_authorization(self):
        experiment = self.experiment
        self.assertFalse(self.client.login(username=experiment.experimenter.email,
                                           password='jibber jabber'))
        self.login_experimenter()


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
        c = self.client
        self.login_experimenter()
        e = self.experiment
        e.activate()
        self.assertTrue(e.participant_set.count() > 0)
        response = c.post('/api/experiment/update', dict(experiment_id=self.experiment.pk, action='clear_participants'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(e.participant_set.count(), 0)

    def test_unauthorized_experimenter_access(self):
        c = self.client
        new_experimenter = self.create_experimenter()
        self.login_experimenter(new_experimenter)
        response = c.post('/api/experiment/update',
                          {'experiment_id': self.experiment.pk, 'action': 'clear_participants'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.experiment.participant_set.count() > 0)

    def test_unauthorized_participant_access(self):
        self.login_participant(self.experiment.participant_set.first())
        response = self.client.post('/api/experiment/update',
                                    {'experiment_id': self.experiment.pk, 'action': 'clear_participants'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.experiment.participant_set.count() > 0)


class ArchiveApiTest(BaseVcwebTest):

    def test_archive(self):
        c = self.client
        self.login_experimenter()
        e = self.experiment
        e.activate()
        self.assertFalse(e.is_archived)
        response = c.post('/api/experiment/update', dict(experiment_id=self.experiment.pk, action='archive'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(e.is_archived)
