#!/usr/bin/env python
import os
import sys
import json
import logging
import redis
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

sys.path.append(
    path.abspath(path.join(path.dirname(path.abspath(__file__)), '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings.local'

TORNADO_LOG_FILENAME = "vcweb-tornado.log"
TORNADO_LOG = path.join(settings.LOG_DIRECTORY, TORNADO_LOG_FILENAME)

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
        'vcweb': {
            'level': 'DEBUG',
            'handlers': ['tornado.file', 'console'],
            'propagate': False,
        },
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

"""
Participant sockjs connection class.
"""
# sockjs-tornado will create new instance for every connected client.
class ParticipantConnection(SockJSConnection):

    def on_open(self, request):
        logger.debug("opening connection %s", request)

    def on_message(self, msg):
        if not msg:
            return
        message_dict = json.loads(msg)
        logger.debug("message: %s", message_dict)

        auth_token = RedisPubSub.get_redis_instance().get(message_dict['user_id'])
        if message_dict['event_type'] == 'connect' and auth_token == message_dict['auth_token']:
            self.group = message_dict['participant_group']
            self.experiment = message_dict['experiment_id']

            # Subscribe to 'experiment' and 'group' message channels
            subscriber.subscribe([RedisPubSub.get_participant_broadcast_channel(self.experiment),
                                  RedisPubSub.get_participant_group_channel(self.group)], self)
        else:
            logger.debug("Failed to connect due to auth_token mismatch. Found (%s) expected (%s)",
                         auth_token, message_dict['auth_token'])

    def on_close(self):
        subscriber.unsubscribe(RedisPubSub.get_participant_broadcast_channel(self.experiment), self)
        subscriber.unsubscribe(RedisPubSub.get_participant_group_channel(self.group), self)


"""
Experimenter sockjs connection class.
"""
class ExperimenterConnection(SockJSConnection):

    def on_open(self, request):
        logger.debug("opening connection %s", request)

    def _send_message(self, message, event_type):
        self.send(json.dumps({'message': message, 'event_type': event_type}))

    def on_message(self, msg):
        if not msg:
            return
        message_dict = json.loads(msg)
        logger.debug("message: %s", message_dict)

        auth_token = RedisPubSub.get_redis_instance().get(message_dict['email'] + "_" + str(message_dict['user_id']))
        if message_dict['event_type'] == 'connect' and auth_token == message_dict['auth_token']:
            # Subscribe to experiment specific 'broadcast' message channels
            self.experiment = message_dict['experiment_id']
            subscriber.subscribe([RedisPubSub.get_experimenter_channel(self.experiment)], self)
            # Send success message to experimenter
            self._send_message("Successfully connected to the Experiment", "info")
        else:
            self._send_message("Failed to connect to the Experiment due to auth_token mismatch", "info")
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
    urls = list(chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls, ]))
    app = web.Application(urls)
    logger.info("starting sockjs server on port %s", port)
    app.listen(port)
    if getattr(settings, 'RAVEN_CONFIG', None):
        app.sentry_client = AsyncSentryClient(settings.RAVEN_CONFIG['dsn'])
    ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    sys.exit(main())
