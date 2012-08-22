#!/usr/bin/env python
import logging
import os
import sys
import tornadoredis
import simplejson as json
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection
from itertools import chain

sys.path.append(os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb.core.models import Experiment, ParticipantGroupRelationship, Experimenter
from vcweb import settings

logger = logging.getLogger('sockjs.vcweb')

class ParticipantConnection(SockJSConnection):
    default_channel = 'vcweb.participant.websocket'
    def __init__(self, *args, **kwargs):
        super(ParticipantConnection, self).__init__(*args, **kwargs)
        self.client = tornadoredis.Client()
        #self.client.connect()
        #self.client.subscribe(self.default_channel)

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        logger.debug("received: " + json_string)
        message_dict = json.loads(json_string)
        logger.debug("received message %s", message_dict)
        experiment_id = message_dict['experiment_id']
        auth_token = message_dict['auth_token']
        experiment = Experiment.objects.get(pk=experiment_id)

    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass

class ExperimenterConnection(SockJSConnection):
    default_channel = 'vcweb.experimenter.websocket'
    def __init__(self, *args, **kwargs):
        super(ExperimenterConnection, self).__init__(*args, **kwargs)
        self.client = tornadoredis.Client()

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def on_message(self, json_string):
        logger.debug("received: " + json_string)
        message_dict = json.loads(json_string)
        logger.debug("received message %s", message_dict)
        experiment_id = message_dict['experiment_id']
        auth_token = message_dict['auth_token']
        experiment = Experiment.objects.get(pk=experiment_id)

    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass


def main(argv=None):
    if argv is None:
        argv = sys.argv
    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else settings.WEBSOCKET_PORT
    ParticipantRouter = SockJSRouter(ParticipantConnection, '/participant')
    ExperimenterRouter = SockJSRouter(ExperimenterConnection, '/experimenter')
    urls = list(chain.from_iterable([ParticipantRouter.urls, ExperimenterRouter.urls, ]))
    app = web.Application(urls)
    logger.info("starting sockjs server on port %s", port)
    app.listen(port)
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())


