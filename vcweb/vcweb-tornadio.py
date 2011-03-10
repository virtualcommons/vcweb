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
store mappings between beaker session ids and ParticipantGroupRelationship pks
'''
class SessionManager:
    ''' associates beaker session ids with ParticipantGroupRelationship.pks '''
    session_id_to_participant = {}
    ''' the reverse mapping, associates ParticipantGroupRelationship.pks with the beaker session '''
    pgr_to_session = {}

    connections_to_experimenters = {}
    experimenters_to_connections = {}

    refresh_json = simplejson.dumps({ 'message_type': 'refresh' })

    def add_experimenter(self, session, incoming_experimenter_pk):
        experimenter_pk = int(incoming_experimenter_pk)
        logger.debug("registering experimenter %s with session %s" %
                (experimenter_pk, session))
        if session in self.connections_to_experimenters:
            self.remove_experimenter(session)
        self.connections_to_experimenters[session] = experimenter_pk
        self.experimenters_to_connections[experimenter_pk] = session

    def remove_experimenter(self, session):
        if session in self.connections_to_experimenters:
            experimenter_pk = self.connections_to_experimenters[session]
            logger.debug("removing experimenter %s" % experimenter_pk)
            del self.connections_to_experimenters[session]
            del self.experimenters_to_connections[experimenter_pk]

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

    '''
    experimenter functions
    '''
    def send_refresh(self, experiment, experimenter_session, experimenter_id=None):
        if experimenter_session in self.connections_to_experimenters:
            experimenter_pk = self.connections_to_experimenters[experimenter_session]
            experimenter = Experimenter.objects.get(pk=experimenter_pk)
            if experiment.experimenter == experimenter:
                for group in experiment.groups.all():
                    for participant_group_pk, session in self.sessions(group):
                        logger.debug("sending refresh message %s to participant %s" %
                                (SessionManager.refresh_json, participant_group_pk))
                        session.send(SessionManager.refresh_json)
            else:
                logger.warning("Experimenter %s tried to refresh experiment %s" %
                        (experimenter, experiment))
        else:
            logger.warning("No experimenter available for session %s" %
                experimenter_session)

    def send_to_experimenter(self, experimenter_pk, json):
        logger.debug("sending %s to experimenter %s" % (json, experimenter_pk))
        if experimenter_pk in self.experimenters_to_connections:
            self.experimenters_to_connections[experimenter_pk].send(json)
        else:
            logger.debug("no experimenter found with pk %s" % experimenter_pk)
            logger.debug("all experimenters: %s" %
                    self.experimenters_to_connections)

    def send_to_group(self, group, json):
        for participant_group_pk, session in self.sessions(group):
            session.send(json)
        experimenter = group.experiment.experimenter
        logger.debug("sending message to experimenter %s" % experimenter)
        self.send_to_experimenter(experimenter.pk, json)

class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)

# global session manager for experimenters + participants
session_manager = SessionManager()

# FIXME: move to core tornado module?
class ExperimenterHandler(SocketConnection):
    def on_open(self, *args, **kwargs):
        try:
            extra = kwargs['extra']
            logger.debug('%s received extra: %s' % (self, extra))
# FIXME: add authentication
            experimenter_id = extra
            session_manager.add_experimenter(self, experimenter_id)
        except Experimenter.DoesNotExist as e:
            logger.warning("Tried to establish connection but there isn't any experimenter with id %s" % experimenter_id)


    def on_message(self, message):
        event = to_event(message)
        logger.debug("%s received message %s" % (self, message))
        if event.type == 'refresh':
            experiment_id = event.experiment_id
            experimenter_id = event.experimenter_id
            experiment = Experiment.objects.get(pk=experiment_id)
            session_manager.send_refresh(experiment, self, experimenter_id)

    def on_close(self):
        session_manager.remove_experimenter(self)

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
            session_manager.add(extra, self, participant_group_rel)
            group = participant_group_rel.group
            message = "Participant %s connected to group %s." % (participant_group_rel.participant_number, group)
            session_manager.send_to_group(group,
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
        participant_group_rel = session_manager.get_participant(self)
        current_round_data = participant_group_rel.group.experiment.current_round_data
        chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_rel,
                message=event.message,
                round_data=current_round_data
                )
        for participant_group_pk, session in session_manager.sessions(participant_group_rel.group):
            session.send(simplejson.dumps({
                "message" : chat_message.as_html,
                "message_type": 'chat',
                }))

    def on_close(self):
        logger.debug("closing %s" % self)
        session_manager.remove(self)

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
