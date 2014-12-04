from ..models import ExperimentConfiguration, Experiment
from .common import BaseVcwebTest
import json
from datetime import datetime


class CreateExperimentTest(BaseVcwebTest):

    def test(self):
        experimenter = self.create_experimenter()
        self.assertTrue(self.login_experimenter(experimenter))
        ec = ExperimentConfiguration.objects.first()
        before_experiment_creation = datetime.now()
        json_response = self.post(self.reverse('core:create_experiment'), {'experiment_configuration_id': ec.pk})
        self.logger.error("json response: %s", json_response)
        response = json.loads(json_response.content)
        self.assertTrue(response['success'])
        experiment_dict = response['experiment']
        self.assertIsNotNone(experiment_dict)
        e = Experiment.objects.get(pk=experiment_dict['pk'])
        self.assertIsNotNone(e)
        self.assertTrue(e.date_created > before_experiment_creation)
        self.assertEqual(experiment_dict['status'], 'INACTIVE')


class CloneExperimentTest(BaseVcwebTest):

    def test_clone(self):
        experimenter = self.create_experimenter()
        self.assertTrue(self.login_experimenter(experimenter))
        response = self.post(self.reverse('core:clone_experiment'),
                             {'experiment_id': self.experiment.pk, 'action': 'clone'})
        experiment_json = json.loads(response.content)
        cloned_experiment = Experiment.objects.get(pk=experiment_json['experiment']['pk'])
        self.assertEqual(cloned_experiment.experiment_metadata, self.experiment.experiment_metadata)
        self.assertEqual(cloned_experiment.experiment_configuration, self.experiment.experiment_configuration)
        self.assertNotEqual(cloned_experiment.experimenter, self.experiment.experimenter)
        self.assertEqual(cloned_experiment.experimenter, experimenter)
