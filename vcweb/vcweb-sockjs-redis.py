#!/usr/bin/env python
import os
from os import path
import sys
from itertools import chain
import json
from sockjs.tornado import SockJSRouter, SockJSConnection
from tornado import web, ioloop

from django.conf import settings

# redefine logger
import logging
import redis
import tornadoredis
import tornadoredis.pubsub

logger = logging.getLogger(__name__)
sys.path.append(
    path.abspath(path.join(path.dirname(path.abspath(__file__)), '..')))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings.local'

DEFAULT_WEBSOCKET_PORT = 8882


redis_client = redis.Redis()
# Create the tornadoredis.Client instance
# and use it for redis channel subscriptions
subscriber = tornadoredis.pubsub.SockJSSubscriber(tornadoredis.Client())

# Our sockjs connection class.
# sockjs-tornado will create new instance for every connected client.
class ParticipantConnection(SockJSConnection):

    def on_open(self, request):
        logger.debug("opening connection %s", request)

    def on_message(self, msg):
        if not msg:
            return

        message_dict = json.loads(msg)

        logger.debug("message: %s", message_dict)
        self.group = message_dict['participant_group_relationship_id']
        self.experiment = message_dict['experiment_id']

        if message_dict['event_type'] == 'connect':
            # Subscribe to 'experiment' and 'group' message channels
            subscriber.subscribe(['experiment_channel.{}'.format(self.experiment),
                                  'group_channel.{}'.format(self.group)], self)

    def on_close(self):
        subscriber.unsubscribe('group_channel.{}'.format(self.group), self)
        subscriber.unsubscribe('experiment_channel.{}'.format(self.experiment), self)


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
            subscriber.subscribe(['experimenter_channel.{}'.format(self.experiment)], self)

    def on_close(self):
        subscriber.unsubscribe('experimenter_channel.{}'.format(self.experiment), self)


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

    print "starting sockjs server on port " + str(port)

    app.listen(port)

    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())
