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
class VcwebSession:
    session_to_participant = {}
    participant_to_session = {}
    session_to_handlers = {}

    def get_participant(self, session):
        logger.debug("trying to retrieve participant group relationship for session id %s" % session)
        logger.debug("maps are %s and %s" % (session_to_participant, participant_to_session))
        return ParticipantGroupRelationship.objects.get(pk=session_to_participant[session])

    def add(self, handler, participant_group_relationship):
        session = handler.session
        session_to_participant[session] = participant_group_relationship.pk
        participant_to_session[participant_group_relationship.pk] = session

    def remove(self, session):
        del participant_to_session[session_to_participant[session]]
        del session_to_participant[session]
        del session_to_handlers[session]


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

handlers = {}
participants = {}
class ChatHandler(SocketIOHandler):
    vcweb_session = VcwebSession()
    def on_open(self, *args, **kwargs):
        ''' parse args / kwargs for participant session info so we know which group
        to route this guy to
        '''

        logger.debug("args are: %s" % str(args))
        logger.debug("kwargs are: %s" % str(kwargs))
        logger.debug("session is %s" % self.session)
        self.send("Welcome. %s" % handlers)
        handlers[self] = None

    def on_message(self, message):
        ''' message is a Python dict via simplejson '''
        logger.debug("received message %s from handler %s" % (message, self))
        logger.debug("handler session is %s" % self.session)
        event = to_event(message)
        if event.type == 'connect':
            participant_group_rel = ParticipantGroupRelationship.objects.get(participant__pk=event.participant_id,
                    group__pk=event.group_id)
            #vcweb_session.add(self, participant_group_rel)
            event.message = "Participant %s joined group %s." % (participant_group_rel.participant, participant_group_rel.group)
# FIXME: add cleanup
            handlers[self.session['output_handle']] = participant_group_rel.pk
            participants[participant_group_rel.pk] = self.session['output_handle']
        else:
            # check session id..
            #participant_group_rel = vcweb_session.get_participant(self.session.id)
            logger.debug("handlers: %s, participants: %s" % (handlers, participants))
            participant_group_rel = ParticipantGroupRelationship.objects.get(pk=handlers[self.session['output_handle']])


        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                                   message=event.message,
                                   round_configuration=participant_group_rel.group.current_round,
                                   experiment=participant_group_rel.group.experiment
                                   )

        for session, participant_group_pk in handlers.items():
            session.session['output_handle'].send(str(chat_message))

    def on_close(self):
        logger.debug("closing %s" % self)
        vcweb_session.remove(self.session.id)

def main():
    # use the routes classmethod to build the correct resource
    defaultRoute = ChatHandler.routes("socket.io/*")
    #configure the Tornado application
    application = tornado.web.Application(
            [(r'/', IndexHandler), defaultRoute],
            enabled_protocols=['websocket', 'xhr-multipart', 'xhr-polling'],
            flash_policy_port=8043,
            socket_io_port=8888,
            # only needed for standalone testing
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            )
    socketio_server = SocketIOServer(application)

if __name__ == "__main__":
    main()
