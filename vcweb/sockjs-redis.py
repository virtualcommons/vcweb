#!/usr/bin/env python
import json
import logging
import os
import sys
from itertools import chain
from logging.config import dictConfig
from os import path
from sockjs.tornado import SockJSRouter, SockJSConnection

from tornado import web, ioloop
from tornadoredis import pubsub
from sentry_sdk.integrations.tornado import TornadoIntegration

import django
import sentry_sdk
import tornadoredis

# assumes containerized execution
sys.path.append('/code')
from vcweb.redis_pubsub import RedisPubSub

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vcweb.settings.prod')
from django.conf import settings

django.setup()

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
subscriber = pubsub.SockJSSubscriber(tornadoredis.Client())


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

    def is_valid(self, auth_token):
        return self.get_auth_token() == auth_token

    def get_auth_token(self):
        key = "%s_%s" % (self.email, self.user_id)
        return RedisPubSub.get_redis_instance().get(key)

    def on_message(self, message):
        if not message:
            logger.warn("Received empty message")
            return
        message_dict = json.loads(message)
        self.email = message_dict['email']
        self.user_id = message_dict['user_id']
        logger.debug("message: %s", message_dict)
        auth_token = message_dict.get('auth_token')
        if self.is_connection_event(message_dict) and self.is_valid(auth_token):
            self.initialize(message_dict)
            subscriber.subscribe(self.redis_channels, self)
            self.info("Real-time connection enabled")
        else:
            self.info("Failed to authenticate with the real-time server. Please try signing out and signing back in.")
            logger.debug("Failed to connect due to auth_token mismatch. Found (%s) expected (%s)",
                         auth_token, self.get_auth_token())

    def on_close(self):
        for channel in self.redis_channels:
            subscriber.unsubscribe(channel, self)


# sockjs-tornado creates a new instance for every connected client.
class ParticipantConnection(RedisSockJSConnection):
    """
    sockjs connection for participants
    """

    def initialize(self, message_dict):
        self.group_id = message_dict['group_id']
        self.experiment_id = message_dict['experiment_id']

    @property
    def redis_channels(self):
        return (RedisPubSub.get_participant_broadcast_channel(self.experiment_id),
                RedisPubSub.get_participant_group_channel(self.group_id))


class ExperimenterConnection(RedisSockJSConnection):
    """
    sockjs connection for experimenters.
    """

    def initialize(self, message_dict):
        self.experiment_id = message_dict['experiment_id']

    @property
    def redis_channels(self):
        return [RedisPubSub.get_experimenter_channel(self.experiment_id)]


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
    if getattr(settings, 'SENTRY_DSN', None):
        sentry_sdk.init(dsn=settings.SENTRY_DSN,
                integrations=[TornadoIntegration()]
                )
    ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    sys.exit(main())
