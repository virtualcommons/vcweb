#!/usr/bin/env python
import os
import sys
import json
import logging
import tornadoredis
import tornadoredis.pubsub

from os import path
from itertools import chain
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado import web, ioloop
from raven.contrib.tornado import AsyncSentryClient

from logging.config import dictConfig

from redis_pubsub import RedisPubSub

from django.conf import settings

sys.path.append(path.abspath(path.join(path.dirname(path.abspath(__file__)), '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

LOG_FILENAME = "sockjs-redis.log"
TORNADO_LOG = path.join(settings.LOG_DIRECTORY, LOG_FILENAME)

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

# Create the tornadoredis.Client instance and use it for redis channel subscriptions
subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())


class RedisSockJSConnection(SockJSConnection):

    """
    Base class for redis sockjs connections.

    on_message is only used on initial connect to establish a push connection from the sockjs server, all other
    communication should be mediated through Django endpoints. A typical real-time request involves a page submitting a
    request to Django, Django notifies the appropriate experiment redis channels, and our sockjs process (pub-subbed
    with Redis) dispatches the json messages as they were received to connected clients.
    """

    def on_open(self, request):
        logger.debug("opening connection for %s", request)

    def _send_message(self, message, event_type):
        self.send(json.dumps({'message': message, 'event_type': event_type}))

    def info(self, message):
        self._send_message(message, 'info')

    def error(self, message):
        self._send_message(message, 'error')

    def is_connection_event(self, message_dict):
        return message_dict['event_type'] == 'connect'

    def is_authenticated(self, message_dict):
        return self.get_auth_token(message_dict) == message_dict.get('auth_token')

    def get_auth_token(self, message_dict):
        key = message_dict['email'] + "_" + message_dict['user_id']
        return RedisPubSub.get_redis_instance().get(key)


# sockjs-tornado creates a new instance for every connected client.
class ParticipantConnection(RedisSockJSConnection):
    """
    sockjs connection for participants
    """

    def on_message(self, msg):
        if not msg:
            return
        message_dict = json.loads(msg)
        logger.debug("message: %s", message_dict)

        auth_token = self.get_auth_token(message_dict)
        if self.is_authenticated(message_dict):
            self.group = message_dict['participant_group']
            self.experiment = message_dict['experiment_id']
            # Subscribe to 'experiment' and 'group' message channels
            subscriber.subscribe([RedisPubSub.get_participant_broadcast_channel(self.experiment),
                                  RedisPubSub.get_participant_group_channel(self.group)],
                                 self)
        else:
            self.error("Failed to authenticate with the real-time server. Please try signing out and signing back in.")
            logger.debug("Failed to connect due to auth_token mismatch. Found (%s) expected (%s)",
                         auth_token, message_dict['auth_token'])

    def on_close(self):
        subscriber.unsubscribe(RedisPubSub.get_participant_broadcast_channel(self.experiment), self)
        subscriber.unsubscribe(RedisPubSub.get_participant_group_channel(self.group), self)


class ExperimenterConnection(RedisSockJSConnection):
    """
    sockjs connection for experimenters.
    """

    def on_message(self, msg):
        if not msg:
            return
        message_dict = json.loads(msg)
        logger.debug("message: %s", message_dict)
        auth_token = self.get_auth_token(message_dict)
        if self.is_authenticated(message_dict):
            # Subscribe to experiment specific 'broadcast' message channels
            self.experiment = message_dict['experiment_id']
            subscriber.subscribe([RedisPubSub.get_experimenter_channel(self.experiment)], self)
            # Send success message to experimenter
            self.info("Real-time connection enabled")
        else:
            self.info("Authentication failed for real-time connection, please try signing out and signing back in.")
            logger.debug("Failed to connect due to auth_token mismatch. Found (%s) expected (%s)",
                         auth_token, message_dict['auth_token'])

    def on_close(self):
        subscriber.unsubscribe(RedisPubSub.get_experimenter_channel(self.experiment), self)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else settings.WEBSOCKET_PORT
    ParticipantRouter = SockJSRouter(ParticipantConnection, '%s/participant' % settings.WEBSOCKET_URI)
    ExperimenterRouter = SockJSRouter(ExperimenterConnection, '%s/experimenter' % settings.WEBSOCKET_URI)
    urls = list(chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls]))
    app = web.Application(urls)
    logger.info("starting sockjs server on port %s", port)
    app.listen(port)
    if getattr(settings, 'RAVEN_CONFIG', None):
        app.sentry_client = AsyncSentryClient(settings.RAVEN_CONFIG['dsn'])
    ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    sys.exit(main())
