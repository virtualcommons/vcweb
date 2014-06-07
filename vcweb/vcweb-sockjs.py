#!/usr/bin/env python
import os
from os import path
import sys
import json
from itertools import chain

from raven.contrib.tornado import AsyncSentryClient
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado import web, ioloop


sys.path.append(
    path.abspath(path.join(path.dirname(path.abspath(__file__)), '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'
from django.conf import settings
from vcweb.core.models import (
    Experiment, ParticipantExperimentRelationship, Experimenter, ChatMessage)

# redefine logger
import logging
from logging.config import dictConfig
TORNADO_LOG_FILENAME = "vcweb-tornado.log"
TORNADO_LOG = path.join(settings.LOG_DIRECTORY, TORNADO_LOG_FILENAME)
DEFAULT_WEBSOCKET_PORT = 8882

dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'DEBUG',
        'handlers': ['tornado.file', 'console'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s [%(name)s|%(funcName)s:%(lineno)d] %(message)s'
        }
    },
    'loggers': {
        'vcweb': {
            'level': 'DEBUG',
            'handlers': ['tornado.file', 'console'],
            'propagate': False,
        },
        'sockjs.vcweb': {
            'level': 'DEBUG',
            'handlers': ['tornado.file', 'console'],
            'propagate': False,
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'tornado.file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': TORNADO_LOG,
            'backupCount': 6,
            'maxBytes': 10000000,
        },
    },
})
logger = logging.getLogger('sockjs.vcweb')


def create_chat_event(message):
    return create_message_event(message, 'chat')


def create_message_event(message, event_type='info'):
    return json.dumps({'message': message, 'event_type': event_type})

REFRESH_EVENT_TYPE = 'refresh'
UPDATE_EVENT_TYPE = 'update'
READY_EVENT_TYPE = 'participant_ready'

REFRESH_EVENT = json.dumps({'event_type': 'refresh'})
UPDATE_EVENT = json.dumps({'event_type': 'update'})
DISCONNECTION_EVENT = create_message_event(
    'Your session has expired and you have been disconnected.  You can only have one window open to a vcweb page.')
UNAUTHORIZED_EVENT = create_message_event(
    "You do not appear to be authorized to perform this action.  If this problem persists, please contact us.")


class ConnectionManager(object):

    '''
    Manages sockjs-tornado connections

    FIXME: Better to replace this with a pub/sub system like redis or zeromq.  Instead of pushing data from the client
    to this real-time server directly and placing experiment logic here we would POST data to django endpoints, which
    then push JSON events into the pub/sub system.  The connection manager observes the pub/sub system and dispatches
    the events appropriately.
    '''
    # bidi maps for (participant.pk, experiment.pk) -> SocketConnection
    connection_to_participant = {}
    participant_to_connection = {}
    # bidi maps for (experimenter.pk, experiment.pk) -> SocketConnection
    connection_to_experimenter = {}
    experimenter_to_connection = {}
    '''
    We use participant_pk + experiment_pk tuples as keys in these bidimaps because
    groups may not have formed yet.
    FIXME: consider refactoring core so that an "all" group always exists in an
    experiment.
    '''

    def __str__(self):
        return u"Participants: %s\nExperimenters: %s" % (self.participant_to_connection, self.experimenter_to_connection)

    def add_experimenter(self, connection, incoming_experimenter_pk, incoming_experiment_pk):
        logger.debug(
            "experimenter_to_connection: %s", self.experimenter_to_connection)
        logger.debug(
            "connection_to_experimenter: %s", self.connection_to_experimenter)
        experimenter_pk = int(incoming_experimenter_pk)
        experiment_id = int(incoming_experiment_pk)
        experimenter_tuple = (experimenter_pk, experiment_id)
        logger.debug(
            "registering experimenter %s with connection %s", experimenter_pk, connection)
# prune old connections
        if experimenter_tuple in self.experimenter_to_connection:
            existing_connection = self.experimenter_to_connection[
                experimenter_tuple]
            if existing_connection:
                existing_connection.send(DISCONNECTION_EVENT)
                del self.connection_to_experimenter[existing_connection]
                existing_connection.close()

        if connection in self.connection_to_experimenter:
            logger.debug("experimenter %s had an existing connection %s ", str(experimenter_tuple),
                         self.connection_to_experimenter[connection])
        self.connection_to_experimenter[connection] = experimenter_tuple
        self.experimenter_to_connection[experimenter_tuple] = connection

    def remove_experimenter(self, connection):
        if connection in self.connection_to_experimenter:
            experimenter_tuple = self.connection_to_experimenter[connection]
            logger.debug("removing experimenter %s", experimenter_tuple)
            del self.connection_to_experimenter[connection]
            if experimenter_tuple in self.experimenter_to_connection:
                del self.experimenter_to_connection[experimenter_tuple]

    def get_participant_group_relationship(self, connection, experiment):
        (participant_pk, experiment_pk) = self.connection_to_participant[
            connection]
        logger.debug(
            "Looking for ParticipantGroupRelationship with tuple (%s, %s)", participant_pk, experiment_pk)
        return experiment.get_participant_group_relationship(participant_pk)

    def get_participant_experiment_tuple(self, connection):
        return self.connection_to_participant[connection]

    def add_participant(self, connection, participant_experiment_relationship):
        logger.debug(
            "connection to participant: %s", self.connection_to_participant)
        logger.debug(
            "participant to connection: %s", self.participant_to_connection)
        participant_tuple = (participant_experiment_relationship.participant.pk,
                             participant_experiment_relationship.experiment.pk)
        if participant_tuple in self.participant_to_connection:
            logger.debug(
                "participant already has a connection, removing previous mappings.")
            self.remove_participant(
                self.participant_to_connection[participant_tuple])

        self.connection_to_participant[connection] = participant_tuple
        self.participant_to_connection[participant_tuple] = connection
        return participant_tuple

    def remove_participant(self, connection):
        try:
            participant_tuple = self.connection_to_participant[connection]
            del self.participant_to_connection[participant_tuple]
            del self.connection_to_participant[connection]
        except KeyError as k:
            logger.warning(
                "caught key error %s while trying to remove participant connection %s", connection, k)

    '''
    Generator function that yields active (participant_group_relationship_id, connection) tuples for the given group
    '''

    def connections(self, group):
        experiment = group.experiment
        for participant_group_relationship in group.participant_group_relationship_set.select_related('participant').all():
            ''' only return currently connected connections in this group '''
            participant = participant_group_relationship.participant
            participant_tuple = (participant.pk, experiment.pk)
            if participant_tuple in self.participant_to_connection:
                yield (participant_group_relationship.pk, self.participant_to_connection[participant_tuple])

    '''
    generator function yielding all (participant group relationship id, connection) tuples for the given experiment
    '''

    def all_participants(self, experimenter, experiment):
        experimenter_key = (experimenter.pk, experiment.pk)
        if experimenter_key in self.experimenter_to_connection:
            for group in experiment.groups:
                for participant_group_relationship_id, connection in self.connections(group):
                    yield (participant_group_relationship_id, connection)
        else:
            logger.warning(
                "No experimenter available in experimenter_to_connection %s", self.experimenter_to_connection)
    '''
    experimenter functions
    '''

    def send_refresh(self, experimenter, experiment):
        return self.broadcast(experiment, REFRESH_EVENT, experimenter)

    def send_update_event(self, experimenter, experiment):
        return self.broadcast(experiment, UPDATE_EVENT, experimenter)

    def send_goto(self, experimenter, experiment, url):
        message = json.dumps({'event_type': 'goto', 'url': url})
        return self.broadcast(experiment, message, experimenter)

    def send_to_experimenter(self, json, experiment_id=None, experimenter_id=None, experiment=None):
        if experimenter_id is None and experiment_id is None:
            experiment_id = experiment.pk
            experimenter_id = experiment.experimenter.pk
        experimenter_tuple = (experimenter_id, experiment_id)
        logger.debug("sending %s to experimenter %s", json, experimenter_id)
        if experimenter_tuple in self.experimenter_to_connection:
            connection = self.experimenter_to_connection[experimenter_tuple]
            logger.debug("sending to connection %s", connection)
            connection.send(json)
        else:
            logger.debug("no experimenter found with pk %s in experimenters set %s", experimenter_tuple,
                         self.experimenter_to_connection)

    def broadcast(self, experiment=None, message=None, experimenter=None, notify_experimenter=True):
        if experimenter is None:
            experimenter = experiment.experimenter
        if message is None:
            logger.error(
                "Tried to broadcast an empty message to %s", experiment)
            raise ValueError(
                "Cannot broadcast an empty message to %s" % experiment)
        participant_connections = []
        for (participant_group_id, connection) in self.all_participants(experimenter, experiment):
            participant_connections.append(participant_group_id)
            connection.send(message)
        logger.debug("sent message %s to %s", message, participant_connections)
        if notify_experimenter:
            self.send_to_experimenter(message, experiment=experiment)
        return participant_connections

    def send_to_group(self, group, event):
        for participant_group_id, connection in self.connections(group):
            connection.send(event)
        self.send_to_experimenter(event, experiment=group.experiment)

connection_manager = ConnectionManager()

# replace with namedtuple


class Struct:

    def to_json(self):
        return json.dumps(self.__dict__)

    def __init__(self, **attributes):
        self.__dict__.update(attributes)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s" % self.__dict__


def to_event(message):
    return Struct(**message)


def verify_auth_token(event):
    try:
        auth_token = event.auth_token
        per = ParticipantExperimentRelationship.objects.select_related(
            'participant').get(pk=event.participant_experiment_relationship_id)
        participant = per.participant
        return per, participant.authentication_token == auth_token
    except ParticipantExperimentRelationship.DoesNotExist:
        logger.error("no participant experiment relationship found for id %s",
                     event.participant_experiment_relationship_id)
        return None, False


class BaseConnection(SockJSConnection):

    def get_handler(self, event_type):
        lexical_handler = 'handle_' + event_type
        handler = getattr(self, lexical_handler, None)
        if handler is None:
            handler = self.default_handler
        logger.debug(
            "invoking handler %s (lexical: %s)", handler, lexical_handler)
        return handler

    def default_handler(self, event, experiment=None, **kwargs):
        logger.warning("%s unhandled message: %s", self, event)


class ParticipantConnection(BaseConnection):
    default_channel = 'vcweb.participant.websocket'

    def __init__(self, *args, **kwargs):
        super(ParticipantConnection, self).__init__(*args, **kwargs)
        #self.client = tornadoredis.Client()
        # self.client.connect()
        # self.client.subscribe(self.default_channel)

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        # self.client.listen(self.on_chan_message)

    def handle_submit(self, event, experiment, **kwargs):
        pass

    def handle_all_participants_ready(self, event, experiment, **kwargs):
        logger.debug(
            "all participants ready to move on to the next round for %s", experiment)
        (per, valid) = verify_auth_token(event)
        if valid:
            connection_manager.send_to_experimenter(create_message_event(
                "All participants are ready to move on to the next round.", event_type="all_participants_ready"), experiment=experiment)
        else:
            logger.warning("Invalid auth token for participant %s", per)
            self.send(UNAUTHORIZED_EVENT)

    def handle_participant_ready(self, event, experiment, **kwargs):
        logger.debug(
            "handling participant ready event %s for experiment %s", event, experiment)
        (per, valid) = verify_auth_token(event)
        if valid:
            if not getattr(event, 'message', None):
                event.message = "Participant %s is ready." % per.participant
            connection_manager.broadcast(experiment, event.to_json())
        else:
            logger.warning("Invalid auth token for participant %s", per)
            self.send(UNAUTHORIZED_EVENT)
        if experiment.all_participants_ready:
            connection_manager.send_to_experimenter(create_message_event(
                "All participants are ready to move on to the next round."), experiment=experiment)

    def handle_connect(self, event, experiment, **kwargs):
        logger.debug("connection event: %s", event)
        (per, valid) = verify_auth_token(event)
        if valid:
            participant_tuple = connection_manager.add_participant(self, per)
            logger.debug("added connection: %s", participant_tuple)
            connection_manager.send_to_experimenter(create_message_event(
                "Participant %s connected." % per.participant), experiment=experiment)
        else:
            self.send(UNAUTHORIZED_EVENT)

    def handle_chat(self, event, experiment, **kwargs):
        (per, valid) = verify_auth_token(event)
        if valid:
            pgr = connection_manager.get_participant_group_relationship(
                self, experiment)
            current_round_data = experiment.current_round_data
            # FIXME: should chat message be created via post to Django form
            # instead?
            chat_message = ChatMessage.objects.create(participant_group_relationship=pgr,
                                                      string_value=event.message,
                                                      round_data=current_round_data
                                                      )
            connection_manager.send_to_group(pgr.group, chat_message.to_json())

    def on_message(self, json_string):
        logger.debug("message: %s", json_string)
        message_dict = json.loads(json_string)
        experiment_id = message_dict['experiment_id']
        experiment = Experiment.objects.select_related(
            'participant_experiment_relationship_set').get(pk=experiment_id)
        # could handle connection here or in on_open, revisit
        event_type = message_dict['event_type']
        handler = self.get_handler(event_type)
        event = to_event(message_dict)
        handler(event, experiment)

    def on_close(self):
        # self.client.unsubscribe(self.default_channel)
        pass


class ExperimenterConnection(BaseConnection):
    default_channel = 'vcweb.experimenter.websocket'

    def __init__(self, *args, **kwargs):
        super(ExperimenterConnection, self).__init__(*args, **kwargs)
        #self.client = tornadoredis.Client()

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        # self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        logger.debug("message: %s", json_string)
        message_dict = json.loads(json_string)
        auth_token = message_dict['auth_token']
        experimenter_id = message_dict['experimenter_id']
        experimenter = Experimenter.objects.get(pk=experimenter_id)
        if experimenter.authentication_token == auth_token:
            event = to_event(message_dict)
            experiment = Experiment.objects.get(pk=event.experiment_id)
            handler = self.get_handler(event.event_type)
            handler(event, experiment, experimenter=experimenter)
            return
        logger.warning(
            "experimenter %s auth tokens didn't match: [%s <=> %s]", experimenter, auth_token, experimenter.authentication_token)
        self.send(create_message_event(
            'Your session has expired, please try logging in again.  If this problem persists, please contact us.'))

    def handle_connect(self, event, experiment, experimenter):
        connection_manager.add_experimenter(
            self, event.experimenter_id, event.experiment_id)
        self.send(
            create_message_event("Experimenter %s connected." % experimenter))

    def handle_refresh(self, event, experiment, experimenter):
        notified_participants = connection_manager.send_refresh(
            experimenter, experiment)
        self.send(create_message_event(
            "Refreshed all connected participant pgr_ids=%s)" % notified_participants))

    def handle_update_participants(self, event, experiment, experimenter):
        notified_participants = connection_manager.send_update_event(
            experimenter, experiment)
        self.send(create_message_event(
            "Updating all connected participants pgr_ids=%s)" % notified_participants))

    def on_close(self):
        # self.client.unsubscribe(self.default_channel)
        pass


def main(argv=None):
    if argv is None:
        argv = sys.argv
    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else DEFAULT_WEBSOCKET_PORT
    ParticipantRouter = SockJSRouter(ParticipantConnection, '/participant')
    ExperimenterRouter = SockJSRouter(ExperimenterConnection, '/experimenter')
    urls = list(
        chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls, ]))
    app = web.Application(urls)
    logger.info("starting sockjs server on port %s", port)
    app.listen(port)
    if getattr(settings, 'RAVEN_CONFIG', None):
        app.sentry_client = AsyncSentryClient(settings.RAVEN_CONFIG['dsn'])
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())
