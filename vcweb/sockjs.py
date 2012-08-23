#!/usr/bin/env python
import logging
import os
import sys
import tornadoredis
import simplejson 
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection
from itertools import chain

sys.path.append(os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import Experiment, ParticipantGroupRelationship, Experimenter
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

    def all_participants(self, connection, experiment):
        if connection in self.connection_to_experimenter:
            (experimenter_pk, experiment_pk) = self.connection_to_experimenter[connection]
            if experiment.pk == experiment_pk:
                for group in experiment.group_set.all():
                    for participant_group_pk, connection in self.connections(group):
                        yield (participant_group_pk, connection)
            else:
                logger.warning("Experimenter %s tried to refresh experiment %s", experimenter_pk, experiment)
        else:
            logger.warning("No experimenter available for connection %s", connection)
    '''
    experimenter functions
    '''
    def send_refresh(self, connection, experiment, experimenter_id=None):
        for (participant_group_pk, connection) in self.all_participants(connection, experiment):
            logger.debug("sending refresh to %s, %s", participant_group_pk, connection)
            connection.send(ConnectionManager.REFRESH_EVENT)

    def send_goto(self, connection, experiment, url):
        notified_participants = []
        json = simplejson.dumps({'message_type': 'goto', 'url': url})
        for (participant_group_pk, connection) in self.all_participants(connection, experiment):
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

class ParticipantConnection(SockJSConnection):
    default_channel = 'vcweb.participant.websocket'
    def __init__(self, *args, **kwargs):
        super(ParticipantConnection, self).__init__(*args, **kwargs)
        self.client = tornadoredis.Client()
        #self.client.connect()
        #self.client.subscribe(self.default_channel)

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #connection_manager.add_participant(self)
        #self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        logger.debug("received: " + json_string)
        message_dict = simplejson.loads(json_string)
        logger.debug("received message %s", message_dict)
        experiment_id = message_dict['experiment_id']
        auth_token = message_dict['auth_token']
        experiment = Experiment.objects.get(pk=experiment_id)

    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass

class ExperimenterConnection(SockJSConnection):
    default_channel = 'vcweb.experimenter.websocket'
    def __init__(self, *args, **kwargs):
        super(ExperimenterConnection, self).__init__(*args, **kwargs)
        self.client = tornadoredis.Client()

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        logger.debug("received: " + json_string)
        message_dict = simplejson.loads(json_string)
        logger.debug("received message %s", message_dict)
        experiment_id = message_dict['experiment_id']
        auth_token = message_dict['auth_token']
        experimenter_id = message_dict['experimenter_id']
        experimenter = Experimenter.objects.get(pk=experimenter_id)
        if (experimenter.authentication_token == auth_token):
            connection_manager.add_experimenter(self, experimenter_id, experiment_id)
        else:
            logger.warning("experimenter %s auth tokens didn't match: [%s <=> %s]", auth_token, experimenter.authentication_token)
        self.send(create_message_event('Experimenter %s connected.' % experimenter))

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
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())


