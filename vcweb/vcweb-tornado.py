#!/usr/bin/env python

import tornado.web
from tornad_io import SocketIOHandler
from tornad_io import SocketIOServer

import os
import sys
import logging
logger = logging.getLogger('vcweb.tornado')

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'
from vcweb.core.models import *

'''
store mappings between beaker session ids and ParticipantGroupRelationship pks
'''
class SessionManager:
    session_id_to_participant = {}
    participant_to_session = {}

    def get_participant(self, session):
        logger.debug("trying to retrieve participant group relationship for session id %s" % session)
        logger.debug("maps are %s and %s" % (self.session_id_to_participant, self.participant_to_session))
        return ParticipantGroupRelationship.objects.get(pk=self.session_id_to_participant[session.id])

    def add(self, session, participant_group_relationship):
        self.session_id_to_participant[session.id] = participant_group_relationship.pk
        self.participant_to_session[participant_group_relationship.pk] = session

    def remove(self, session):
        participant_group_pk = self.session_id_to_participant[session.id]
        del self.participant_to_session[participant_group_pk]
        del self.session_id_to_participant[session.id]

    def sessions(self, group):
        participant_ids = [ pgr.pk for pgr in group.participant_group_relationships.all() ]
        for pgr_id in participant_ids:
            if pgr_id in self.participant_to_session:
                yield (pgr_id, self.participant_to_session[pgr_id])
            pass

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


session_manager = SessionManager()

class MessageHandler(SocketIOHandler):
    def on_open(self, *args, **kwargs):
        ''' parse args / kwargs for participant session info so we know which group
        to route this guy to
        '''
        logger.debug("args are: %s" % str(args))
        logger.debug("kwargs are: %s" % str(kwargs))
        logger.debug("session is %s" % self.session)

    def on_message(self, message):
        ''' incoming JSON message gets converted to a Python dict via simplejson '''
        logger.debug("received message %s from handler %s" % (message, self))
        logger.debug("handler session is %s" % self.session)
        event = to_event(message)
        if event.type == 'connect':
            participant_group_rel = ParticipantGroupRelationship.objects.get(participant__pk=event.participant_id,
                    group__pk=event.group_id)
            event.message = "Participant %s joined group %s." % (participant_group_rel.participant, participant_group_rel.group)
# FIXME: add cleanup
            session_manager.add(self.session, participant_group_rel)
        else:
            # check session id..
            participant_group_rel = session_manager.get_participant(self.session)


        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                                   message=event.message,
                                   round_configuration=participant_group_rel.group.current_round,
                                   experiment=participant_group_rel.group.experiment
                                   )

        for participant_group_pk, session in session_manager.sessions(participant_group_rel.group):
            session['output_handle'].send(str(chat_message))

    def on_close(self):
        logger.debug("closing %s" % self)
        session_manager.remove(self.session)

def main():
    # use the routes classmethod to build the correct resource
    messageRoute = MessageHandler.routes("socket.io/*")
    #configure the Tornado application
    application = tornado.web.Application(
            [(r'/', IndexHandler), messageRoute],
            enabled_protocols=['websocket', 'xhr-multipart', 'xhr-polling'],
            flash_policy_port=8043,
            socket_io_port=8888,
            # only needed for standalone testing
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            )
    socketio_server = SocketIOServer(application)

if __name__ == "__main__":
    main()
