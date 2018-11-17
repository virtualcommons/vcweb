import random

from datetime import datetime, date
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import RequestFactory, Client
from django.utils.http import urlencode

from ..models import (Experiment, Experimenter, ExperimentConfiguration, RoundConfiguration, Parameter, ExperimentGroup,
                      User, PermissionGroup, Participant, ParticipantSignup, Institution, ExperimentSession, Invitation)

import logging

logger = logging.getLogger(__name__)


class BaseVcwebTest(TestCase):

    """
    base class for vcweb.core tests, sets up test fixtures for participants,
    and a number of participants, experiments, etc.
    """
    DEFAULT_EXPERIMENTER_PASSWORD = 'test.experimenter'
    DEFAULT_EXPERIMENTER_EMAIL = 'vcweb.test@mailinator.com'
    DEFAULT_INSTITUTION_NAME = 'Arizona State University'

    def get_default_institution(self):
        return Institution.objects.get(name=self.DEFAULT_INSTITUTION_NAME)

    def load_experiment(self, experiment_metadata=None, experimenter_password=None, **kwargs):
        if experiment_metadata is None:
            # FIXME: assumes that there is always some Experiment available to load. revisit this, or figure out some
            # better way to bootstrap tests
            experiment = Experiment.objects.first().clone()
        else:
            experiment = self.create_new_experiment(experiment_metadata, **kwargs)
        if experimenter_password is None:
            experimenter_password = BaseVcwebTest.DEFAULT_EXPERIMENTER_PASSWORD
        # currently associating all available Parameters with this
        # ExperimentMetadata
        if not experiment.experiment_metadata.parameters.exists():
            experiment.experiment_metadata.parameters.add(
                *Parameter.objects.values_list('pk', flat=True))
        experiment.experiment_configuration.round_configuration_set.exclude(sequence_number=1).update(duration=60)
        experiment.save()
        u = experiment.experimenter.user
        u.set_password(experimenter_password)
        u.save()
        return experiment

    @property
    def login_url(self):
        return reverse('core:login')

    @property
    def profile_url(self):
        return reverse('core:profile')

    @property
    def dashboard_url(self):
        return reverse('core:dashboard')

    @property
    def update_experiment_url(self):
        return reverse('core:update_experiment')

    @property
    def check_email_url(self):
        return reverse('core:check_email')

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

    def update_experiment(self, action=None, **kwargs):
        kwargs.update(experiment_id=self.experiment.pk, action=action)
        return self.post(self.update_experiment_url, kwargs)

    def reverse(self, viewname, query_parameters=None, **kwargs):
        reversed_url = reverse(viewname, **kwargs)
        if query_parameters is not None:
            return '%s?%s' % (reversed_url, urlencode(query_parameters))
        return reversed_url

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

    def create_new_experiment(self, experiment_metadata, experimenter=None, number_of_rounds=10):
        """
        Creates a new Experiment and ExperimentConfiguration based on the given ExperimentMetadata.
        """
        if experimenter is None:
            experimenter = self.demo_experimenter
        experiment_configuration = ExperimentConfiguration.objects.create(experiment_metadata=experiment_metadata,
                                                                          name='Test Experiment Configuration',
                                                                          exchange_rate=0.02,
                                                                          creator=experimenter)
        for index in range(1, number_of_rounds):
            should_initialize = (index == 1)
            experiment_configuration.round_configuration_set.create(sequence_number=index,
                                                                    randomize_groups=should_initialize,
                                                                    initialize_data_values=should_initialize)
        return Experiment.objects.create(experimenter=experimenter,
                                         experiment_metadata=experiment_metadata,
                                         experiment_configuration=experiment_configuration)

    def add_participants(self, demo_participants=True, number_of_participants=None, participant_emails=None,
                         test_email_suffix='asu.edu', **kwargs):
        if number_of_participants is None:
            # set default number of participants to max group size * 2
            number_of_participants = self.experiment.experiment_configuration.max_group_size * 2
        experiment = self.experiment
        if demo_participants:
            if experiment.participant_set.count() == 0:
                logger.debug("no participants found. adding %d participants to %s", number_of_participants, experiment)
                experiment.setup_demo_participants(email_suffix=test_email_suffix,
                                                   count=number_of_participants, password='test')
        else:
            if participant_emails is None:
                # generate participant emails
                participant_emails = ['test.%d@asu.edu' % index for index in range(0, number_of_participants)]
            self.experiment.register_participants(emails=participant_emails, password='test')
            # XXX: should can_receive_invitations automatically be set to true in Experiment.register_participants
            # instead?
            self.experiment.participant_set.update(can_receive_invitations=True)

    def setUp(self, **kwargs):
        self.client = Client()
        self.factory = RequestFactory()
        self.experiment = self.load_experiment(**kwargs)
        self.add_participants(**kwargs)
        self.logger = logger
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
        u = User.objects.create_user(
            username=email, email=email, password=password)
        u.groups.add(PermissionGroup.experimenter.get_django_group())
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

    def post(self, url, *args, **kwargs):
        if ':' in url:
            url = self.reverse(url)
        response = self.client.post(url, *args, **kwargs)
        self.reload_experiment()
        return response

    def get(self, url, *args, **kwargs):
        if ':' in url:
            url = self.reverse(url)
        return self.client.get(url, *args, **kwargs)

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
        return ExperimentGroup.objects.create(number=1, max_size=max_size, experiment=experiment)

    class Meta:
        abstract = True


class SubjectPoolTest(BaseVcwebTest):

    def setup_participants(self, number=500):
        password = "test"
        participants = []
        institution = self.get_default_institution()
        genders = [g[0] for g in Participant.GENDER_CHOICES]
        class_statuses = [c[0] for c in Participant.CLASS_CHOICES][:4]
        for x in range(number):
            email = 'student%s@asu.edu' % x
            user = User.objects.create_user(first_name='Student', last_name='%d' % x, username=email, email=email,
                                            password=password)
            # Assign the user to participant permission group
            user.groups.add(PermissionGroup.participant.get_django_group())
            user.save()
            year = random.choice(list(range(1980, 1995)))
            month = random.choice(list(range(1, 12)))
            day = random.choice(list(range(1, 28)))
            random_date = datetime(year, month, day)
            p = Participant(
                user=user,
                can_receive_invitations=random.choice([True, False]),
                gender=random.choice(genders),
                birthdate=random_date,
                major='Complex Adaptive Systems',
                class_status=random.choice(class_statuses),
                institution=institution
            )
            participants.append(p)
        Participant.objects.bulk_create(participants)
        return participants

    def setup_experiment_sessions(self, capacity=1, location="Online", number=4, start_date=None):
        e = self.experiment
        experiment_session_pks = []
        today = date.today()
        year = today.year
        month = today.month
        for x in range(number):
            if start_date is None:
                day = random.choice(list(range(1, 29)))
                start_date = datetime(year, month, day)
            es = ExperimentSession.objects.create(
                experiment_metadata=e.experiment_metadata,
                scheduled_date=start_date,
                scheduled_end_date=start_date,
                capacity=capacity,
                location=location,
                creator=e.experimenter.user,
            )
            experiment_session_pks.append(es.pk)
        return experiment_session_pks

    def get_final_participants(self):
        potential_participants = list(Participant.objects.invitation_eligible(
            self.experiment_metadata.pk, institution_name=self.get_default_institution().name))
        potential_participants_count = len(potential_participants)
        # logger.debug(potential_participants)
        number_of_invitations = 50

        final_participants = []
        if potential_participants_count > 0:
            if potential_participants_count < number_of_invitations:
                final_participants = potential_participants
            else:
                final_participants = random.sample(potential_participants, number_of_invitations)
        return final_participants

    def setup_participant_signup(self, participant_list, es_pk_list):
        participant_list = participant_list[:25]
        participant_signups = []
        for participant in participant_list:
            inv = Invitation.objects.filter(participant=participant,
                                            experiment_session__pk__in=es_pk_list).order_by('?')[:1]
            participant_signups.append(
                ParticipantSignup(invitation=inv[0],
                                  attendance=random.choice([0, 1, 2, 3])))
        ParticipantSignup.objects.bulk_create(participant_signups)

    def initialize(self, number_of_participants=50, start_date=None, number_of_experiment_sessions=5):
        es_pks = self.setup_experiment_sessions(start_date=start_date, number=number_of_experiment_sessions)
        self.setup_participants(number=number_of_participants)
        participants = Participant.objects.all()
        self.setup_invitations(participants, es_pks)
        self.setup_participant_signup(participants, es_pks)

    def setup_invitations(self, participants, es_pk_list):
        invitations = []
        experiment_sessions = ExperimentSession.objects.filter(pk__in=es_pk_list)
        user = self.demo_experimenter.user
        today = date.today()
        year = today.year
        month = today.month

        for participant in participants:
            # recipient_list.append(participant.email)
            for es in experiment_sessions:
                day = random.choice(list(range(1, 29)))
# FIXME: what is the point of setting date_created to random dates in this month & year?
                random_date = datetime(year, month, day)
                invitations.append(Invitation(participant=participant, experiment_session=es, date_created=random_date,
                                              sender=user))
        Invitation.objects.bulk_create(invitations)
