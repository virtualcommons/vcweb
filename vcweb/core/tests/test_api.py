from ..models import ExperimentConfiguration, Experiment, ChatMessage
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


class SaveExperimentNoteTest(BaseVcwebTest):

    def test_current_round(self):
        experimenter = self.experimenter
        e = self.experiment
        e.activate()
        self.assertTrue(self.login_experimenter(experimenter))
        note = "Some harrowing detail about the current round"
        response = self.post('core:save_experimenter_notes',
                             {'experiment_id': self.experiment.pk, 'notes': note})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])
        self.assertEqual(e.current_round_data.experimenter_notes, note)
        e.advance_to_next_round()
        self.assertFalse(e.current_round_data.experimenter_notes)
        second_note = "Second round note"
        response = self.post('core:save_experimenter_notes',
                             {'experiment_id': self.experiment.pk, 'notes': second_note})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['success'])
        self.assertEqual(e.current_round_data.experimenter_notes, second_note)
        # make sure that the previous note still exists
        self.assertEqual(e.get_round_data(e.previous_round).experimenter_notes, note)


class HandleChatMessageTest(BaseVcwebTest):

    def test(self):
        e = self.experiment
        e.activate()
        for pgr in e.participant_group_relationships:
            self.assertTrue(self.login_participant(pgr.participant))
            response = self.post(self.reverse('core:handle_chat_message', args=(e.pk,)),
                                 {'participant_group_id': pgr.pk, 'message': "Chat message from %s" % pgr})
            self.assertEqual(200, response.status_code)
            self.assertTrue(json.loads(response.content)['success'])
            self.assertEqual(ChatMessage.objects.get(participant_group_relationship=pgr).string_value,
                             'Chat message from %s' % pgr)
