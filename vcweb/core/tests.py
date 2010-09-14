"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.

"""

from django.test import TestCase
from vcweb.core.models import Experiment, Experimenter, ExperimentConfiguration, \
    Participant, ParticipantExperimentRelationship, Group, ExperimentMetadata
import logging
import signals

logger = logging.getLogger('vcweb.core.tests')

class BaseVcwebTest(TestCase):
    fixtures = ['test_users_participants', 'forestry_test_data']

    def setUp(self):
        self.participants = Participant.objects.all()
        self.experiment = Experiment.objects.get(pk=1)
        self.experimenter = Experimenter.objects.get(pk=1)
        self.experiment_metadata = ExperimentMetadata.objects.get(pk=1)
        self.experiment_configuration = ExperimentConfiguration.objects.get(pk=1)

    def create_new_experiment(self):
        e = Experiment(experimenter=self.experimenter, experiment_configuration=self.experiment_configuration, experiment_metadata=self.experiment_metadata)
        e.save()
        return e

    def create_new_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        g = Group(number=1, max_size=max_size, experiment=experiment)
        g.save()
        return g



    class Meta:
        abstract = True

class ExperimentTest(BaseVcwebTest):

    def round_started_test_handler(self, experiment_id=None, time=None, round_configuration_id=None, **kwargs):
        logger.debug("invoking round started test handler with args experiment_id:%i time:%s round_configuration_id:%s"
                     % (experiment_id, time, round_configuration_id))
        self.failUnlessEquals(experiment_id, self.experiment.pk)
        self.failUnlessEquals(round_configuration_id, self.experiment.get_current_round().id)
        self.failUnless(time, "time should be set")
        raise Exception


    def test_start(self):
        signals.round_started.connect(self.round_started_test_handler, sender=None)
        try:
            self.experiment.start()
            self.fail("Should have raised an exception.")
        except Exception:
            logger.debug("expected exception raised.")
            self.failUnless(self.experiment.is_running())

    def test_allocate_groups(self):
        self.experiment.allocate_groups(randomize=False)
        self.failUnlessEqual(self.experiment.groups.count(), 2, "should be 2 groups after non-randomized allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            group = p.get_group(self.experiment)
            self.failIf(participant_number <= 0 or participant_number > group.max_size)
            self.failUnlessEqual(participant_number % group.max_size, p.id % group.max_size)
            logger.debug("randomized participant number %i (id: %i)" % (participant_number, p.pk))



    def test_get_participant_number(self):
        self.experiment.allocate_groups()
        self.failUnlessEqual(self.experiment.groups.count(), 2, "Should have two groups after allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            self.failUnless(participant_number > 0, 'participant number should be greater than 0')
            logger.debug("participant number %i (id: %i)" % (participant_number, p.pk))

class GroupTest(BaseVcwebTest):
    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.create_new_group(max_size=10, experiment=self.experiment)
        count = 0;
        for p in self.participants:
            g.add_participant(p)
            count += 1
            self.assertTrue(g.participants)
            self.failUnlessEqual(g.participants.count(), count, "group.participants size should be %i" % count)
            self.failUnlessEqual(g.size, count, "group size should be %i" % count)


class ParticipantExperimentRelationshipTest(BaseVcwebTest):

    def test_participant_identifier(self):
        """ exercises the generation of participant_identifier """
        e = self.create_new_experiment()
        for p in self.participants:
            per = ParticipantExperimentRelationship(participant=p, experiment=e, created_by=self.experimenter.user)
            per.save()
            self.failUnless(per.id > 0)
            logger.debug("Participant identifier is %s - sequential id is %i" % (per.participant_identifier, per.sequential_participant_identifier))
            self.failUnless(per.participant_identifier)
            self.failUnless(per.sequential_participant_identifier > 0)

        self.failUnlessEqual(e.participants.count(), self.participants.count())







