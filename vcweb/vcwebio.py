#!/usr/bin/env python
import tornado.web
from tornadio import SocketConnection, get_router, server
import os
import sys
import logging
import simplejson

sys.path.append(os.path.abspath('..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import ParticipantExperimentRelationship, ParticipantGroupRelationship, ChatMessage, Experimenter, Experiment
from vcweb import settings

# FIXME: currently tornadio.vcweb to avoid confusion with vcweb loggers
logger = logging.getLogger('tornadio.vcweb')

def info_json(message):
    return simplejson.dumps({'message_type': 'info', 'message': message})

def goto_json(url):
    return simplejson.dumps({'message_type': 'goto', 'url': url})

def chat_json(chat_message):
    return simplejson.dumps({
        "pk": chat_message.pk,
        "date_created": chat_message.date_created.strftime("%H:%M:%S"),
        "message" : unicode(chat_message),
        "message_type": 'chat',
        })

class ConnectionManager:
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
    refresh_json = simplejson.dumps({ 'message_type': 'refresh' })

    def add_experimenter(self, connection, incoming_experimenter_pk, incoming_experiment_pk):
        logger.debug("experimenter_to_connection: %s", self.experimenter_to_connection)
        logger.debug("connection_to_experimenter: %s", self.connection_to_experimenter)
        experimenter_pk = int(incoming_experimenter_pk)
        experiment_id = int(incoming_experiment_pk)
        experimenter_tuple = (experimenter_pk, experiment_id)
        logger.debug("registering experimenter %s with connection %s", experimenter_pk, connection)
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
        if connection in self.connection_to_participant:
            (participant_pk, experiment_pk) = self.connection_to_participant[connection]
            logger.debug("Looking for ParticipantGroupRelationship with tuple (%s, %s)", participant_pk, experiment_pk)
            return ParticipantGroupRelationship.objects.get(participant__pk=participant_pk, group__experiment__pk = experiment_pk)
        logger.warning("Couldn't find a participant group relationship using connection %s in connection map %s", connection, self.connection_to_participant)
        return None

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
        for participant_group_relationship in group.participant_group_relationships.all():
            ''' only return currently connected connections in this group '''
            participant = participant_group_relationship.participant
            participant_tuple = (participant.pk, experiment.pk)
            if participant_tuple in self.participant_to_connection:
                yield (participant_group_relationship.pk, self.participant_to_connection[participant_tuple])

    def all_participants(self, connection, experiment):
        if connection in self.connection_to_experimenter:
            (experimenter_pk, experiment_pk) = self.connection_to_experimenter[connection]
            if experiment.pk == experiment_pk:
                for group in experiment.groups.all():
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
            connection.send(ConnectionManager.refresh_json)

    def send_goto(self, connection, experiment, url):
        notified_participants = []
        json = simplejson.dumps({'message_type': 'goto', 'url': url})
        for (participant_group_pk, connection) in self.all_participants(connection, experiment):
            connection.send(json)
            notified_participants.append(participant_group_pk)
        return notified_participants


    def send_to_experimenter(self, experimenter_tuple, json):
        (experimenter_pk, experiment_pk) = experimenter_tuple
        logger.debug("sending %s to experimenter %s", json, experimenter_tuple)
        if experimenter_tuple in self.experimenter_to_connection:
            connection = self.experimenter_to_connection[experimenter_tuple]
            logger.debug("sending to connection %s", connection)
            connection.send(json)
        else:
            logger.debug("no experimenter found with pk %s", experimenter_pk)
            logger.debug("all experimenters: %s", self.experimenter_to_connection)

    def send_to_group(self, group, json):
        for participant_group_pk, connection in self.connections(group):
            connection.send(json)
        experiment = group.experiment
        experimenter = experiment.experimenter
        self.send_to_experimenter((experimenter.pk, experiment.pk), json)

# replace with namedtuple
class Struct:
    def __init__(self, **attributes):
        self.__dict__.update(attributes)

def to_event(message):
    return Struct(**message)

# connection manager for experimenters + participants
connection_manager = ConnectionManager()
# FIXME: move to a core tornado module?
class ExperimenterHandler(SocketConnection):
    # FIXME: add authentication
    def on_open(self, *args, **kwargs):
        try:
            extra = kwargs['extra']
            logger.debug('%s received extra: %s', self, extra)
            experimenter_id = extra
        except Experimenter.DoesNotExist:
            logger.warning("Tried to establish connection but there isn't any experimenter with id %s", experimenter_id)

    def on_message(self, message):
        event = to_event(message)
        logger.debug("%s received message %s", self, message)
        if event.message_type == 'connect':
            connection_manager.add_experimenter(self, event.experimenter_id, event.experiment_id)
        elif event.message_type == 'refresh':
            experiment_id = event.experiment_id
            experimenter_id = event.experimenter_id
            experiment = Experiment.objects.get(pk=experiment_id)
            connection_manager.send_refresh(self, experiment, experimenter_id)
            self.send(info_json("Refreshed all participants"))
        elif event.message_type == 'goto':
            experiment_id = event.experiment_id
            experiment = Experiment.objects.get(pk=experiment_id)
            url = event.message
            notified_participants = connection_manager.send_goto(self, experiment, url)
            self.send(info_json("Sent goto:%s to all participants" % url))
            logger.debug("sending all connected participants %s to %s", notified_participants, url)

    def on_close(self):
        logger.debug("removing experimenter connection %s", self)
        connection_manager.remove_experimenter(self)

class ParticipantHandler(SocketConnection):
    # FIXME: on_open authenticates or prepares the session
    def on_open(self, *args, **kwargs):
        # FIXME: verify user auth tokens
        extra = kwargs['extra']
        #(auth_token, dot, participant_group_relationship_id) = extra.partition('.')
        #logger.debug("auth token: %s, id %s" % (auth_token, participant_group_relationship_id))
        relationship_id = extra
        try:
            participant_experiment_relationship = ParticipantExperimentRelationship.objects.select_related(depth=1).get(pk=relationship_id)
            connection_manager.add_participant(extra, self, participant_experiment_relationship)
            participant_group_rel = connection_manager.get_participant_group_relationship(self)
            if participant_group_rel is not None:
                group = participant_group_rel.group
                message = "Participant %s (%s) connected." % (participant_group_rel.participant_number, group)
                connection_manager.send_to_group(group,
                        simplejson.dumps({
                            'message' : message,
                            'message_type': 'info',
                            }))
            else:
                experimenter_tuple = (participant_experiment_relationship.experiment.experimenter.pk,
                        participant_experiment_relationship.experiment.pk)
                connection_manager.send_to_experimenter(experimenter_tuple,
                        simplejson.dumps({
                            'message': "Participant %s connected to experiment." % participant_experiment_relationship,
                            'message_type': 'info',
                            }))
        except KeyError as e:
            logger.debug("no participant group relationship id %s", e)
        except ParticipantExperimentRelationship.DoesNotExist as e:
            logger.debug("no participant experiment relationship with id %s (%s)", relationship_id, e)

    def on_message(self, message, *args, **kwargs):
        logger.debug("received message %s from handler %s", message, self)
        event = to_event(message)
        # could handle connection here or in on_open, revisit
        if 'connect' in event.message_type:
            return
        elif event.message_type == 'submit':
            (participant_pk, experiment_pk) = connection_manager.get_participant_experiment_tuple(self)
            experiment = Experiment.objects.get(pk=experiment_pk)
            logger.debug("processing participant submission for participant %s and experiment %s", participant_pk, experiment)
            # sanity check, make sure this is a data round.
            if experiment.is_data_round_in_progress:
                experimenter_tuple = (experiment.experimenter.pk, experiment.pk)
                event.participant_pk = participant_pk
                pgr_pk = event.participant_group_relationship_id
                participant_group_relationship = ParticipantGroupRelationship.objects.get(pk=pgr_pk)
                prdv = experiment.current_round_data.participant_data_values.get(participant_group_relationship__pk=pgr_pk)
                event.participant_data_value_pk = prdv.pk
                event.participant_number = participant_group_relationship.participant_number
                event.participant_group = participant_group_relationship.group_number
                json = simplejson.dumps(event.__dict__)
                logger.debug("submit event json: %s", json)
                connection_manager.send_to_experimenter(experimenter_tuple, json)
                if experiment.all_participants_have_submitted:
                    connection_manager.send_to_experimenter(
                            experimenter_tuple,
                            info_json('All participants have submitted a decision.'))
            else:
                logger.debug("No data round in progress, received late submit event: %s", event)

        elif event.message_type == 'chat':
            participant_group_relationship = connection_manager.get_participant_group_relationship(self)
            current_round_data = participant_group_relationship.group.experiment.current_round_data
            chat_message = ChatMessage.objects.create(participant_group_relationship=participant_group_relationship,
                    message=event.message,
                    round_data=current_round_data
                    )
            chat_json = simplejson.dumps({
                "pk": chat_message.pk,
                'round_data_pk': current_round_data.pk,
                'participant': unicode(participant_group_relationship.participant),
                "date_created": chat_message.date_created.strftime("%H:%M:%S"),
                "message" : unicode(chat_message),
                "message_type": 'chat',
                })
            connection_manager.send_to_group(participant_group_relationship.group, chat_json)

    def on_close(self):
        logger.debug("removing participant connection %s", self)
        connection_manager.remove_participant(self)

def main(argv=None):
    if argv is None:
        argv = sys.argv
    participantRouter = get_router(ParticipantHandler, resource="participant", extra_re=r'\d+', extra_sep='/')
    # router w/ auth hash..
    #participantRouter = tornadio.get_router(ChatHandler, resource="chat", extra_re=r'[\w._=]+', extra_sep='/')
    experimenterRouter = get_router(ExperimenterHandler, resource="experimenter", extra_re=r'\d+', extra_sep='/')
    #configure the Tornado application
    # currently only allow one command-line argument, the port to run on.
    port = int(argv[1]) if (len(argv) > 1) else settings.SOCKET_IO_PORT

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
