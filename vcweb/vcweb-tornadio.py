#!/usr/bin/env python

import tornado.web
from tornadio import SocketConnection, get_router, server

import os
import sys
import logging

logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import ParticipantGroupRelationship, ChatMessage

'''
store mappings between beaker session ids and ParticipantGroupRelationship pks
'''
class SessionManager:
    ''' associates beaker session ids with ParticipantGroupRelationship.pks '''
    session_id_to_participant = {}
    ''' the reverse mapping, associates ParticipantGroupRelationship.pks with the beaker session '''
    pgr_to_session = {}

    experimenter_connections = {}
    connections_to_experimenters = {}

    def add_experimenter(self, session, experimenter):
        experimenter_connections[session] = experimenter.pk
        connections_to_experimenters[experimenter.pk] = session


    def get_participant(self, session):
        logger.debug("trying to retrieve participant group relationship for session id %s" % session)
        logger.debug("maps are %s and %s" % (self.session_id_to_participant, self.pgr_to_session))
        return ParticipantGroupRelationship.objects.get(pk=self.session_id_to_participant[session])

    def add(self, auth_token, session, participant_group_relationship):
        if participant_group_relationship.pk in self.pgr_to_session:
            logger.debug("participant already has a session, removing previous mappings.")
            self.remove(self.pgr_to_session[participant_group_relationship.pk])

        self.session_id_to_participant[session] = participant_group_relationship.pk
        self.pgr_to_session[participant_group_relationship.pk] = session

    def remove(self, session):
        try:
            participant_group_pk = self.session_id_to_participant[session]
            del self.pgr_to_session[participant_group_pk]
            del self.session_id_to_participant[session]
        except KeyError, k:
            logger.warning( "caught key error %s while trying to remove session %s" % (session, k) )
            pass

    '''
    Generator function that yields (participant_group_relationship_id, beaker session object) tuples
    for the given group
    '''
    def sessions(self, group):
        pgr_ids = [ pgr.pk for pgr in group.participant_group_relationships.all() ]
        for pgr_id in pgr_ids:
            ''' only return currently connected sessions in this group '''
            if pgr_id in self.pgr_to_session:
                yield (pgr_id, self.pgr_to_session[pgr_id])
            pass

    def send_to_group(self, group, message):
        for participant_group_pk, session in self.sessions(group):
            session.send(message)

class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)

class IndexHandler(tornado.web.RequestHandler):
    """Test HTTP handler to serve the chatroom page if we hit host:8888 manually"""
    def get(self):
        self.render("chat.html")


class ExperimenterHandler(SocketConnection):
    def on_open(self, *args, **kwargs):
        try:
            extra = kwargs['extra']
            logger.debug('%s received extra: %s' % (self, extra))
# FIXME: add authentication
            experimenter_id = extra
            session_manager.add_experimenter(self, Experimenter.objects.get(pk=experimenter_id))
        except Experimenter.DoesNotExist as e:
            logger.warning("Tried to establish connection but there isn't any experimenter with id %s" % experimenter_id)


    def on_message(self, message):
        event = to_event(message)
        logger.debug("%s received message %s" % (self, message))

    def on_close(self):
        session_manager.remove_experimenter(self)

                    
'''
FIXME: make this a class / instance var on ChatHandler? But then it forces us to
type ChatHandler.session_manager instead of just session_manager...
'''
session_manager = SessionManager()

class ChatHandler(SocketConnection):

    def on_open(self, *args, **kwargs):
        try:
            # FIXME: verify user auth tokens
            extra = kwargs['extra']
            logger.debug('%s received extra: %s' % (self, extra))
            #(auth_token, dot, participant_group_relationship_id) = extra.partition('.')
            #logger.debug("auth token: %s, id %s" % (auth_token, participant_group_relationship_id))
            participant_group_relationship_id = extra
            participant_group_rel = ParticipantGroupRelationship.objects.get(pk=participant_group_relationship_id)
            session_manager.add(extra, self, participant_group_rel)
            group = participant_group_rel.group
            message = "<div>Participant %s joined group %s chat.</div>" % (participant_group_rel.participant_number, group)
            session_manager.send_to_group(group, message)
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
        if event.type == 'connect':
            return
        # FIXME: add authentication
        participant_group_rel = session_manager.get_participant(self)
        current_round_data = participant_group_rel.group.experiment.current_round_data
        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                message=event.message,
                round_data=current_round_data
                )
        for participant_group_pk, session in session_manager.sessions(participant_group_rel.group):
            session.send(chat_message.as_html)

    def on_close(self):
        logger.debug("closing %s" % self)
        session_manager.remove(self)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    # use the routes classmethod to build the correct resource
    chatRouter = get_router(ChatHandler, resource="chat", extra_re=r'\d+', extra_sep='/')
    #chatRouter = tornadio.get_router(ChatHandler, resource="chat", extra_re=r'[\w._=]+', extra_sep='/')
    #configure the Tornado application
    # currently only allow one command-line argument, the port to run on.
    port = int(argv[1]) if (len(argv) > 1) else 8888

    application = tornado.web.Application(
            [(r'/', IndexHandler), chatRouter.route(), ],
            flash_policy_port=8043,
            flash_policy_file='/etc/nginx/flashpolicy.xml',
            socket_io_port=port,
            # only needed for standalone testing
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            )
    return server.SocketServer(application)

if __name__ == "__main__":
    sys.exit(main())
