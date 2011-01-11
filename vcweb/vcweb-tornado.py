#!/usr/bin/env python

import tornado.web
from tornad_io import SocketIOHandler
from tornad_io import SocketIOServer

import os
import sys

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'
from vcweb.core.models import *

import logging

logger = logging.getLogger('vcweb.tornad.io')


'''
mapping of participant_group_relationship pks to tuples (socket.io handler, participant_group_relationship)
Map<Integer, (SocketIOHandler, ParticipantGroupRelationship)
'''
participant_id_to_handler = {}
handler_to_participant_group_relationship = {}

class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)
'''
need something to listen on one amqp exchange/channel for server-bound
messages, and another to listen on another amqp exchange/channel for
client-bound messages
'''


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("chat.html")

class ChatHandler(SocketIOHandler):
    """Socket.IO handler"""

    def on_open(self, *args, **kwargs):
        ''' parse args / kwargs for participant session info so we know which group
        to route this guy to
        '''

        logger.debug("args are: %s" % str(args))
        logger.debug("kwargs are: %s" % str(kwargs))
        number_of_participants = len(participant_id_to_handler) + 1
        self.send("Welcome!  There are currently %s members logged in." % number_of_participants)

    def on_message(self, message):
        ''' message is a Python dict via simplejson '''
        logger.debug("received message %s" % message)
        event = to_event(message)
        if event.type == 'connect':
            participant_group_rel = ParticipantGroupRelationship.objects.get(participant__pk=event.participant_id,
                    group__pk=event.group_id)
            if participant_group_rel.pk in participant_id_to_handler:
                existing_handler = participant_id_to_handler[participant_group_rel.pk]
                logger.debug("removing existing participant handler %s" %
                        existing_handler)
                existing_handler.on_close()
            participant_id_to_handler[participant_group_rel.pk] = self
            handler_to_participant_group_relationship[self] = participant_group_rel
            event.message = "Participant %s joined group %s." % (participant_group_rel.participant, participant_group_rel.group)

        
        for participant_group_rel_pk, handler in participant_id_to_handler.items():
            handler.send('Participant %s: %s' % (Participant.objects.get(pk=event.participant_id), event.message))

    def on_close(self):
        logger.debug("closing %s" % self)
        participant = handler_to_participant_group_relationship[self]
        try:
            del participant_id_to_handler[participant.pk] 
            del handler_to_participant_group_relationship[self]
        except KeyError as e:
            logger.error("Couldn't fully remove self %s - key: %s" % (self, e))

# use the routes classmethod to build the correct resource
defaultRoute = ChatHandler.routes("socket.io/*")

#configure the Tornado application
application = tornado.web.Application(
    [(r'/', IndexHandler), defaultRoute],
    enabled_protocols = ['websocket', 'xhr-multipart', 'xhr-polling'],
    flash_policy_port = 8043,
    socket_io_port = 8888,
# only needed for standalone testing
    static_path = os.path.join(os.path.dirname(__file__), "static"),
)

if __name__ == "__main__":
    socketio_server = SocketIOServer(application)
