#!/usr/bin/env python
import logging
import os
import sys
import simplejson
from itertools import chain
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado import web, ioloop
from tornado.escape import xhtml_escape
from raven.contrib.tornado import AsyncSentryClient
import tornadoredis

sys.path.append(os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import Experiment, ParticipantGroupRelationship, Participant, Experimenter, ChatMessage
from vcweb import settings

logger = logging.getLogger('sockjs.vcweb')

class ConnectionManager(object):
    '''
    Manages socket.io connections to tornadio.
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
    REFRESH_EVENT = simplejson.dumps({ 'message_type': 'refresh' })
    DISCONNECTION_EVENT = simplejson.dumps({ 'message_type': 'info', 'message': 'Your session has expired and you have been disconnected.  You can only have one window open to a vcweb page.'})

    def __str__(self):
        return u"Participants: %s\nExperimenters: %s" % (self.participant_to_connection, self.experimenter_to_connection)

    def add_experimenter(self, connection, incoming_experimenter_pk, incoming_experiment_pk):
        logger.debug("experimenter_to_connection: %s", self.experimenter_to_connection)
        logger.debug("connection_to_experimenter: %s", self.connection_to_experimenter)
        experimenter_pk = int(incoming_experimenter_pk)
        experiment_id = int(incoming_experiment_pk)
        experimenter_tuple = (experimenter_pk, experiment_id)
        logger.debug("registering experimenter %s with connection %s", experimenter_pk, connection)
# prune old connections
        if experimenter_tuple in self.experimenter_to_connection:
            existing_connection = self.experimenter_to_connection[experimenter_tuple]
            if existing_connection:
                existing_connection.send(self.DISCONNECTION_EVENT)
                del self.connection_to_experimenter[existing_connection]

        if connection in self.connection_to_experimenter:
            logger.debug("this experimenter has an existing connection (%s <-> %s) ",
                    self.connection_to_experimenter[connection], experimenter_tuple)
        self.connection_to_experimenter[connection] = experimenter_tuple
        self.experimenter_to_connection[experimenter_tuple] = connection

    def remove_experimenter(self, connection):
        if connection in self.connection_to_experimenter:
            experimenter_tuple = self.connection_to_experimenter[connection]
            logger.debug("removing experimenter %s", experimenter_tuple)
            del self.connection_to_experimenter[connection]
            if experimenter_tuple in self.experimenter_to_connection:
                del self.experimenter_to_connection[experimenter_tuple]

    def get_participant_group_relationship(self, connection):
        (participant_pk, experiment_pk) = self.connection_to_participant[connection]
        logger.debug("Looking for ParticipantGroupRelationship with tuple (%s, %s)", participant_pk, experiment_pk)
        return ParticipantGroupRelationship.objects.get(participant__pk=participant_pk, group__experiment__pk = experiment_pk)

    def get_participant_experiment_tuple(self, connection):
        return self.connection_to_participant[connection]

    def add_participant(self, auth_token, connection, participant_experiment_relationship):
        logger.debug("connection to participant: %s", self.connection_to_participant)
        logger.debug("participant to connection: %s", self.participant_to_connection)
        participant_tuple = (participant_experiment_relationship.participant.pk, participant_experiment_relationship.experiment.pk)
        if participant_tuple in self.participant_to_connection:
            logger.debug("participant already has a connection, removing previous mappings.")
            self.remove_participant(self.participant_to_connection[participant_tuple])

        self.connection_to_participant[connection] = participant_tuple
        self.participant_to_connection[participant_tuple] = connection
        return participant_tuple

    def remove_participant(self, connection):
        try:
            participant_tuple = self.connection_to_participant[connection]
            del self.participant_to_connection[participant_tuple]
            del self.connection_to_participant[connection]
        except KeyError as k:
            logger.warning("caught key error %s while trying to remove participant connection %s", connection, k)

    '''
    Generator function that yields (participant_group_relationship_id, connection) tuples
    for the given group
    '''
    def connections(self, group):
        experiment = group.experiment
        for participant_group_relationship in group.participant_group_relationship_set.select_related(depth=1).all():
            ''' only return currently connected connections in this group '''
            participant = participant_group_relationship.participant
            participant_tuple = (participant.pk, experiment.pk)
            if participant_tuple in self.participant_to_connection:
                yield (participant_group_relationship.pk, self.participant_to_connection[participant_tuple])

    def all_participants(self, experimenter, experiment):
        experimenter_key = (experimenter.pk, experiment.pk)
        if experimenter_key in self.experimenter_to_connection:
            for group in experiment.group_set.all():
                for participant_group_relationship_id, connection in self.connections(group):
                    yield (participant_group_relationship_id, connection)
        else:
            logger.warning("No experimenter available in experimenter_to_connection %s", self.experimenter_to_connection)
    '''
    experimenter functions
    '''
    def send_refresh(self, experimenter, experiment):
        participant_connections = []
        for (participant_group_pk, connection) in self.all_participants(experimenter, experiment):
            logger.debug("sending refresh to %s, %s", participant_group_pk, connection)
            participant_connections.append(participant_group_pk)
            connection.send(ConnectionManager.REFRESH_EVENT)
        return participant_connections

    def send_goto(self, experimenter, experiment, url):
        notified_participants = []
        json = simplejson.dumps({'message_type': 'goto', 'url': url})
        for (participant_group_pk, connection) in self.all_participants(experimenter, experiment):
            connection.send(json)
            notified_participants.append(participant_group_pk)
        return notified_participants

    def send_to_experimenter(self, experimenter_tuple, json):
        logger.debug("sending %s to experimenter %s", json, experimenter_tuple)
        if experimenter_tuple in self.experimenter_to_connection:
            connection = self.experimenter_to_connection[experimenter_tuple]
            logger.debug("sending to connection %s", connection)
            connection.send(json)
        else:
            logger.debug("no experimenter found with pk %s in experimenters set %s", experimenter_tuple,
                    self.experimenter_to_connection)

    def send_to_group(self, group, json):
        for participant_group_pk, connection in self.connections(group):
            connection.send(json)
        experiment = group.experiment
        experimenter = experiment.experimenter
        self.send_to_experimenter((experimenter.pk, experiment.pk), json)

connection_manager = ConnectionManager()

def create_message_event(message, message_type='info'):
    return simplejson.dumps({ 'message': message, 'message_type': message_type})

# replace with namedtuple
class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u"%s" % self.__dict__


def to_event(message):
    return Struct(**message)

class BaseConnection(SockJSConnection):
    def get_handler(self, message_type):
        lexical_handler = 'handle_' + message_type
        handler = getattr(self, lexical_handler, None)
        if handler is None:
            handler = self.default_handler
        logger.debug("invoking handler %s (lexical: %s)", handler, lexical_handler)
        return handler

    def default_handler(self, event, experiment=None, **kwargs):
        logger.warning("unhandled message: %s", event)


class ParticipantConnection(BaseConnection):
    default_channel = 'vcweb.participant.websocket'
    def __init__(self, *args, **kwargs):
        super(ParticipantConnection, self).__init__(*args, **kwargs)
        #self.client = tornadoredis.Client()
        #self.client.connect()
        #self.client.subscribe(self.default_channel)

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def handle_submit(self, event, experiment, **kwargs):
        pass

    def handle_connect(self, event, experiment, **kwargs):
        logger.debug("connection event: %s", event)
        auth_token = event.auth_token
        participant_group_id = event.participant_group_relationship_id
        per = ParticipantGroupRelationship.objects.select_related('participant').get(pk=participant_group_id)
        if pgr.participant.authentication_token == auth_token:
            connection_manager.add_participant(

        

    def handle_refresh(self, experimenter, experiment, event):
        notified_participants = connection_manager.send_refresh(experimenter, experiment)
        self.send(create_message_event("Refreshed %s participants" % notified_participants))

    def on_message(self, json_string):
        logger.debug("message: %s", json_string)
        message_dict = simplejson.loads(json_string)
        experiment_id = message_dict['experiment_id']
        auth_token = message_dict['auth_token']
        experiment = Experiment.objects.select_related('participant_experiment_relationship_set').get(pk=experiment_id)
        # could handle connection here or in on_open, revisit
        message_type = message_dict['message_type']
        handler = self.get_handler(message_type)
        # FIXME: verify auth token
        event = to_event(message_dict)
        handler(event, experiment)

        (participant_pk, experiment_pk) = connection_manager.get_participant_experiment_tuple(self)
        participant = Participant.objects.get(pk=participant_pk)
        if participant.authentication_token != auth_token:
            self.send(create_message_event("Your do not appear to be authorized to perform this action.  If this problem persists, please contact us."))
            logger.warning("participant %s auth tokens didn't match [%s <=> %s]", participant,
                    participant.authentication_token, auth_token)
            return
        if message_type == 'submit':
            logger.debug("processing participant submission for participant %s and experiment %s", participant_pk, experiment)
            # sanity check, make sure this is a data round.
            if experiment.is_data_round_in_progress:
                # FIXME: forward the submission event directly to the experimenter, we don't need to save anything as it
                # should be processed directly by posting to the django side of things
                experimenter_tuple = (experiment.experimenter.pk, experiment.pk)
                event.participant_pk = participant_pk
                pgr_pk = event.participant_group_relationship_id
                participant_group_relationship = ParticipantGroupRelationship.objects.get(pk=pgr_pk)

                prdv = experiment.current_round_data.participant_data_value_set.get(participant_group_relationship__pk=pgr_pk)
                event.participant_data_value_pk = prdv.pk
                event.participant_number = participant_group_relationship.participant_number
                event.participant_group = participant_group_relationship.group_number
                json = simplejson.dumps(event.__dict__)
                logger.debug("submit event json: %s", json)
                connection_manager.send_to_experimenter(experimenter_tuple, json)
                if experiment.all_participants_have_submitted:
                    connection_manager.send_to_experimenter(
                            experimenter_tuple,
                            create_message_event('All participants have submitted a decision.'))
            else:
                logger.debug("No data round in progress, received late submit event: %s", event)

        elif message_type == 'chat':
            try:
                participant_group_relationship = connection_manager.get_participant_group_relationship(self)
                current_round_data = participant_group_relationship.group.experiment.current_round_data
# FIXME:  escape on output instead of input
                chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                        value=xhtml_escape(event.message),
                        round_data=current_round_data
                        )
                chat_json = simplejson.dumps({
                    "pk": chat_message.pk,
                    'round_data_pk': current_round_data.pk,
                    'participant': unicode(participant_group_relationship.participant),
                    "date_created": chat_message.date_created.strftime("%H:%M:%S"),
                    "message" : xhtml_escape(unicode(chat_message)),
                    "message_type": 'chat',
                    })
                connection_manager.send_to_group(participant_group_relationship.group, chat_json)
            except:
                logger.warning("Couldn't find a participant group relationship using connection %s with connection manager %s", self, self.connection_manager)


    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass

class ExperimenterConnection(SockJSConnection):
    default_channel = 'vcweb.experimenter.websocket'
    def __init__(self, *args, **kwargs):
        super(ExperimenterConnection, self).__init__(*args, **kwargs)
        #self.client = tornadoredis.Client()

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        message_dict = simplejson.loads(json_string)
        auth_token = message_dict['auth_token']
        experimenter_id = message_dict['experimenter_id']
        experimenter = Experimenter.objects.get(pk=experimenter_id)
        if experimenter.authentication_token == auth_token:
            event = to_event(message_dict)
            experiment = Experiment.objects.get(pk=event.experiment_id)
            handler = self.get_handler(event.message_type)
            handler(event, experiment, experimenter=experimenter)
            return
        logger.warning("experimenter %s auth tokens didn't match: [%s <=> %s]", auth_token, experimenter.authentication_token)
        self.send(create_message_event('Your session has expired, please try logging in again.  If this problem persists, please contact us.'))

    def handle_connect(self, event, experiment, experimenter):
        connection_manager.add_experimenter(self, event.experimenter_id, event.experiment_id)
        self.send(create_message_event("Experimenter %s connected." % experimenter))

    def handle_refresh(self, event, experiment, experimenter):
        notified_participants = connection_manager.send_refresh(experimenter, experiment)
        self.send(create_message_event("Refreshed %s participants" % notified_participants))

    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass


def main(argv=None):
    if argv is None:
        argv = sys.argv
    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else settings.WEBSOCKET_PORT
    ParticipantRouter = SockJSRouter(ParticipantConnection, '/participant')
    ExperimenterRouter = SockJSRouter(ExperimenterConnection, '/experimenter')
    urls = list(chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls, ]))
    app = web.Application(urls)
    logger.info("starting sockjs server on port %s", port)
    app.listen(port)
    app.sentry_client = AsyncSentryClient('http://d266113006054187b70e3af60d9561f3:4f0f8608122b4749a38f8a3a11d0b662@vcweb.asu.edu:9000/1')
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())


