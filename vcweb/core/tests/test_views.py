from .common import BaseVcwebTest


class LoginTest(BaseVcwebTest):

    def test_anonymous_required(self):
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
        self.assertTrue(self.client.login(username=experiment.experimenter.email,
                                          password=BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD))


class ParticipantViewTest(BaseVcwebTest):

    def test_account_profile(self):
        e = self.experiment
        e.activate()
        c = self.client
        for p in e.participant_set.all():
            self.assertFalse(p.is_profile_complete)
            self.assertTrue(c.login(username=p.email, password='test'))
            response = c.get('/dashboard/')
            self.assertEqual(302, response.status_code)
            self.assertTrue('/accounts/profile/' in response.url)

    def test_dashboard(self):
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
