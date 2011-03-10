#!/usr/bin/env python

import tornado.web
from tornadio import SocketConnection, get_router, server
import os
import sys
import logging
import simplejson

logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import ParticipantGroupRelationship, ChatMessage, Experimenter, Experiment

'''
Manages socket.io connections to tornadio.
'''
class ConnectionManager:
    connection_to_participant = {}
    participant_to_connection = {}

    connection_to_experimenter = {}
# (experimenter.pk, experiment.id) -> connection
    experimenter_to_connection = {}

    refresh_json = simplejson.dumps({ 'message_type': 'refresh' })

    def add_experimenter(self, connection, incoming_experimenter_pk, incoming_experiment_pk):
        experimenter_pk = int(incoming_experimenter_pk)
        experiment_id = int(incoming_experiment_pk)
        logger.debug("registering experimenter %s with connection %s" %
                (experimenter_pk, connection))
        if connection in self.connection_to_experimenter:
            self.remove_experimenter(connection)
        self.connection_to_experimenter[connection] = (experimenter_pk, experiment_id)
        self.experimenter_to_connection[(experimenter_pk, experiment_id)] = connection

    def remove_experimenter(self, connection):
        if connection in self.connection_to_experimenter:
            (experimenter_pk, experiment_id) = self.connection_to_experimenter[connection]
            logger.debug("removing experimenter %s" % experimenter_pk)
            del self.connection_to_experimenter[connection]
            del self.experimenter_to_connection[(experimenter_pk, experiment_id)]

    def get_participant(self, connection):
        logger.debug("trying to retrieve participant group relationship for connection id %s" % connection)
        logger.debug("maps are %s and %s" % (self.connection_to_participant,
            self.participant_to_connection))
        return ParticipantGroupRelationship.objects.get(pk=self.connection_to_participant[connection])

    def add(self, auth_token, connection, participant_group_relationship):
        if participant_group_relationship.pk in self.participant_to_connection:
            logger.debug("participant already has a connection, removing previous mappings.")
            self.remove(self.participant_to_connection[participant_group_relationship.pk])

        self.connection_to_participant[connection] = participant_group_relationship.pk
        self.participant_to_connection[participant_group_relationship.pk] = connection

    def remove(self, connection):
        try:
            participant_group_pk = self.connection_to_participant[connection]
            del self.participant_to_connection[participant_group_pk]
            del self.connection_to_participant[connection]
        except KeyError, k:
            logger.warning( "caught key error %s while trying to remove connection %s" % (connection, k) )
            pass

    '''
    Generator function that yields (participant_group_relationship_id, connection) tuples
    for the given group
    '''
    def connections(self, group):
        pgr_ids = [ pgr.pk for pgr in group.participant_group_relationships.all() ]
        for pgr_id in pgr_ids:
            ''' only return currently connected connections in this group '''
            if pgr_id in self.participant_to_connection:
                yield (pgr_id, self.participant_to_connection[pgr_id])
            pass

    '''
    experimenter functions
    '''
    def send_refresh(self, connection, experiment, experimenter_id=None):
        if connection in self.connection_to_experimenter:
            (experimenter_pk, experiment_pk) = self.connection_to_experimenter[connection]
            if experiment.pk == experiment_pk:
                for group in experiment.groups.all():
                    for participant_group_pk, connection in self.connections(group):
                        logger.debug("sending refresh message %s to participant %s" %
                                (ConnectionManager.refresh_json, participant_group_pk))
                        connection.send(ConnectionManager.refresh_json)
            else:
                logger.warning("Experimenter %s tried to refresh experiment %s" %
                        (experimenter_pk, experiment))
        else:
            logger.warning("No experimenter available for connection %s" %
                connection)

    def send_to_experimenter(self, experimenter_tuple, json):
        (experimenter_pk, experiment_pk) = experimenter_tuple
        logger.debug("sending %s to experimenter %s" % (json, experimenter_tuple))
        if experimenter_tuple in self.experimenter_to_connection:
            connection = self.experimenter_to_connection[experimenter_tuple]
            logger.debug("sending to connection %s" % connection)
            connection.send(json)
        else:
            logger.debug("no experimenter found with pk %s" % experimenter_pk)
            logger.debug("all experimenters: %s" % self.experimenter_to_connection)

    def send_to_group(self, group, json):
        for participant_group_pk, connection in self.connections(group):
            connection.send(json)
        experiment = group.experiment
        experimenter = experiment.experimenter
        self.send_to_experimenter((experimenter.pk, experiment.pk), json)

class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)

# global connection manager for experimenters + participants
connection_manager = ConnectionManager()

# FIXME: move to core tornado module?
class ExperimenterHandler(SocketConnection):
    def on_open(self, *args, **kwargs):
        try:
            extra = kwargs['extra']
            logger.debug('%s received extra: %s' % (self, extra))
# FIXME: add authentication
            experimenter_id = extra
        except Experimenter.DoesNotExist as e:
            logger.warning("Tried to establish connection but there isn't any experimenter with id %s" % experimenter_id)


    def on_message(self, message):
        event = to_event(message)
        logger.debug("%s received message %s" % (self, message))
        if event.type == 'connect':
            connection_manager.add_experimenter(self, event.experimenter_id, event.experiment_id)
        elif event.type == 'refresh':
            experiment_id = event.experiment_id
            experimenter_id = event.experimenter_id
            experiment = Experiment.objects.get(pk=experiment_id)
            connection_manager.send_refresh(self, experiment, experimenter_id)
            logger.debug("pinging back to experimenter")
            self.send(simplejson.dumps({'message':"Refreshed all participants", 'message_type':"info"}))

    def on_close(self):
        connection_manager.remove_experimenter(self)

class ParticipantHandler(SocketConnection):
    def on_open(self, *args, **kwargs):
        try:
            # FIXME: verify user auth tokens
            extra = kwargs['extra']
            logger.debug('%s received extra: %s' % (self, extra))
            #(auth_token, dot, participant_group_relationship_id) = extra.partition('.')
            #logger.debug("auth token: %s, id %s" % (auth_token, participant_group_relationship_id))
            participant_group_relationship_id = extra
            participant_group_rel = ParticipantGroupRelationship.objects.get(pk=participant_group_relationship_id)
            connection_manager.add(extra, self, participant_group_rel)
            group = participant_group_rel.group
            message = "Participant %s connected to group %s." % (participant_group_rel.participant_number, group)
            connection_manager.send_to_group(group,
                    simplejson.dumps({
                        'message' : message,
                        'message_type': 'info',
                        }))
        except KeyError, e:
            logger.debug("no participant group relationship id %s" % e)
            pass
        except ParticipantGroupRelationship.DoesNotExist, e:
            logger.debug("no participant group relationship with id %s (%s)" %
                    (participant_group_relationship_id, e))
            pass
        logger.debug("args are: %s" % str(args))
        logger.debug("kwargs are: %s" % str(kwargs))

    def on_message(self, message, *args, **kwargs):
        logger.debug("received message %s from handler %s" % (message, self))
        event = to_event(message)
        if 'connect' in event.type:
            return
        # FIXME: add authentication
        participant_group_rel = connection_manager.get_participant(self)
        current_round_data = participant_group_rel.group.experiment.current_round_data
        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                message=event.message,
                round_data=current_round_data
                )
        for participant_group_pk, connection in connection_manager.connections(participant_group_rel.group):
            connection.send(simplejson.dumps({
                "message" : chat_message.as_html,
                "message_type": 'chat',
                }))

    def on_close(self):
        logger.debug("closing %s" % self)
        connection_manager.remove(self)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    participantRouter = get_router(ParticipantHandler, resource="participant", extra_re=r'\d+', extra_sep='/')
    # router w/ auth hash..
    #participantRouter = tornadio.get_router(ChatHandler, resource="chat", extra_re=r'[\w._=]+', extra_sep='/')
    experimenterRouter = get_router(ExperimenterHandler, resource="experimenter", extra_re=r'\d+', extra_sep='/')
    #configure the Tornado application
    # currently only allow one command-line argument, the port to run on.
    port = int(argv[1]) if (len(argv) > 1) else 8888

    application = tornado.web.Application(
            [participantRouter.route(), experimenterRouter.route(), ],
            flash_policy_port=8043,
            flash_policy_file='/etc/nginx/flashpolicy.xml',
            socket_io_port=port,
            # only needed for standalone testing
#            static_path=os.path.join(os.path.dirname(__file__), "static"),
            )
    return server.SocketServer(application)

if __name__ == "__main__":
    sys.exit(main())
