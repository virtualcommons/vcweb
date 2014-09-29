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

        if message_dict['event_type'] == 'connect':
            self.group = message_dict['participant_group']
            self.experiment = message_dict['experiment_id']

            # Subscribe to 'experiment' and 'group' message channels
            subscriber.subscribe([RedisPubSub.get_participant_broadcast_channel(self.experiment),
                                  RedisPubSub.get_participant_group_channel(self.group)], self)

    def on_close(self):
        subscriber.unsubscribe(RedisPubSub.get_participant_broadcast_channel(self.experiment), self)
        subscriber.unsubscribe(RedisPubSub.get_participant_group_channel(self.group), self)


"""
Experimenter sockjs connection class.
"""
class ExperimenterConnection(SockJSConnection):

    def on_open(self, request):
        logger.debug("opening connection %s", request)

    def on_message(self, msg):
        if not msg:
            return
        message_dict = json.loads(msg)
        logger.debug("message: %s", message_dict)

        if message_dict['event_type'] == 'connect':
            # Subscribe to experiment specific 'broadcast' message channels
            self.experiment = message_dict['experiment_id']
            subscriber.subscribe([RedisPubSub.get_experimenter_channel(self.experiment)], self)

    def on_close(self):
        subscriber.unsubscribe(RedisPubSub.get_experimenter_channel(self.experiment), self)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else DEFAULT_WEBSOCKET_PORT

    ParticipantRouter = SockJSRouter(ParticipantConnection, '/participant')
    ExperimenterRouter = SockJSRouter(ExperimenterConnection, '/experimenter')

    urls = list(
        chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls, ]))

    app = web.Application(urls)

    logger.info("starting sockjs server on port %s", port)

    app.listen(port)

    if getattr(settings, 'RAVEN_CONFIG', None):
        app.sentry_client = AsyncSentryClient(settings.RAVEN_CONFIG['dsn'])

    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())
