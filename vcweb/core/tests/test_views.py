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


class DashboardViewTest(BaseVcwebTest):

    def test_participant_login(self):
        e = self.experiment
        e.activate()
        c = self.client
        for p in e.participant_set.all():
            self.assertTrue(c.login(username=p.email, password='test'))
            response = c.get('/dashboard')
            self.assertEqual(200, response.status_code)
