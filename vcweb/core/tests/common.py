from django.conf import settings
from django.test import TestCase
from django.test.client import RequestFactory, Client

from ..models import (Experiment, Experimenter, ExperimentConfiguration, RoundConfiguration, Parameter, Group, User,
                      PermissionGroup)

import logging

logger = logging.getLogger(__name__)


class BaseVcwebTest(TestCase):

    """
    base class for vcweb.core tests, sets up test fixtures for participants,
    and a number of participants, experiments, etc.
    """
    DEFAULT_EXPERIMENTER_PASSWORD = 'test.experimenter'
    DEFAULT_EXPERIMENTER_EMAIL = 'vcweb.test@mailinator.com'

    def load_experiment(self, experiment_metadata=None, experimenter_password=None, **kwargs):
        if experiment_metadata is None:
            # FIXME: assumes that there is always some Experiment available to load. revisit this, or figure out some
            # better way to bootstrap tests
            experiment = Experiment.objects.first().clone()
        else:
            experiment = self.create_new_experiment(experiment_metadata, **kwargs)
        if experimenter_password is None:
            experimenter_password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD

        self.experiment = experiment
        # currently associating all available Parameters with this
        # ExperimentMetadata
        if not experiment.experiment_metadata.parameters.exists():
            experiment.experiment_metadata.parameters.add(*Parameter.objects.values_list('pk', flat=True))
        experiment.experiment_configuration.round_configuration_set.exclude(sequence_number=1).update(duration=60)
        experiment.save()
        u = experiment.experimenter.user
        u.set_password(experimenter_password)
        u.save()
        return experiment

    @property
    def experiment_metadata(self):
        return self.experiment.experiment_metadata

    @property
    def experiment_configuration(self):
        return self.experiment.experiment_configuration

    @property
    def experimenter(self):
        return self.experiment.experimenter

    @property
    def round_configurations(self):
        return self.experiment_configuration.round_configuration_set

    @property
    def participants(self):
        return self.experiment.participant_set.all()

    @property
    def participant_group_relationships(self):
        return self.experiment.participant_group_relationships

    def login(self, *args, **kwargs):
        return self.client.login(*args, **kwargs)

    def login_participant(self, participant, password='test'):
        return self.client.login(username=participant.email, password=password)

    def login_experimenter(self, experimenter=None, password=None):
        if experimenter is None:
            experimenter = self.experimenter
        if password is None:
            password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD
        return self.client.login(username=experimenter.email, password=password)

    def create_new_experiment(self, experiment_metadata, experimenter=None):
        """
        Creates a new Experiment and ExperimentConfiguration based on the given ExperimentMetadata.
        """
        if experimenter is None:
            experimenter = self.demo_experimenter
        experiment_configuration = ExperimentConfiguration.objects.create(experiment_metadata=experiment_metadata,
                                                                          name='Test Experiment Configuration',
                                                                          creator=experimenter)
        for index in xrange(1, 10):
            should_initialize = (index == 1)
            experiment_configuration.round_configuration_set.create(sequence_number=index,
                                                                    randomize_groups=should_initialize,
                                                                    initialize_data_values=should_initialize)
        return Experiment.objects.create(experimenter=experimenter,
                                         experiment_metadata=experiment_metadata,
                                         experiment_configuration=experiment_configuration)

    def add_test_participants(self, test_email_suffix='asu.edu', number_of_participants=None, **kwargs):
        experiment = self.experiment
        if experiment.participant_set.count() == 0:
            logger.debug("adding participants to %s", experiment)
            if number_of_participants is None:
                # set default number of participants to max group size * 2
                number_of_participants = experiment.experiment_configuration.max_group_size * 2
            experiment.setup_test_participants(email_suffix=test_email_suffix,
                                               count=number_of_participants, password='test')

    def setUp(self, **kwargs):
        self.client = Client()
        self.factory = RequestFactory()
        self.load_experiment(**kwargs)
        self.add_test_participants(**kwargs)
        logging.disable(settings.DISABLED_TEST_LOGLEVEL)

    @property
    def demo_experimenter(self):
        if getattr(self, '_demo_experimenter', None) is None:
            self._demo_experimenter = Experimenter.objects.get(user__email=settings.DEMO_EXPERIMENTER_EMAIL)
        return self._demo_experimenter

    def create_experimenter(self, email=None, password=None):
        if email is None:
            email = BaseVcwebTest.DEFAULT_EXPERIMENTER_EMAIL
        if password is None:
            password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD
        u = User.objects.create_user(username=email, email=email, password=password)
        u.groups.add(PermissionGroup.experimenter.get_django_group())
        logger.error("user groups: %s", u.groups.all())
        return Experimenter.objects.create(user=u, approved=True)

    def advance_to_data_round(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            if e.current_round.is_playable_round:
                return e
            e.advance_to_next_round()

    def reload_experiment(self):
        self.experiment = Experiment.objects.get(pk=self.experiment.pk)
        return self.experiment

    def post(self, *args, **kwargs):
        response = self.client.post(*args, **kwargs)
        self.reload_experiment()
        return response

    def get(self, *args, **kwargs):
        return self.client.get(*args, **kwargs)

    def all_data_rounds(self):
        e = self.experiment
        e.activate()
        while e.has_next_round:
            if e.current_round.is_playable_round:
                yield self.experiment
            e.advance_to_next_round()

    def create_new_round_configuration(self, round_type='REGULAR', template_filename='', template_id=''):
        return RoundConfiguration.objects.create(experiment_configuration=self.experiment_configuration,
                                                 sequence_number=(
                                                     self.experiment_configuration.last_round_sequence_number + 1),
                                                 round_type=round_type,
                                                 template_filename=template_filename,
                                                 template_id=template_id)

    def create_parameter(self, name='test.parameter', scope=Parameter.Scope.EXPERIMENT, parameter_type='string'):
        return Parameter.objects.create(creator=self.experimenter, name=name, scope=scope, type=parameter_type)

    def create_group(self, max_size=10, experiment=None):
        if not experiment:
            experiment = self.experiment
        return Group.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True
