#!/usr/bin/env python
import logging
import os
import sys
import tornadoredis
from tornado import web, ioloop
from sockjs.tornado import SockJSRouter, SockJSConnection

sys.path.append(os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'

from vcweb import settings

logger = logging.getLogger(__name__)

class VcwebConnection(SockJSConnection):
    default_channel = 'vcweb.websocket'
    def __init__(self, *args, **kwargs):
        super(VcwebConnection, self).__init__(*args, **kwargs)
        self.client = tornadoredis.Client()
        #self.client.connect()
        #self.client.subscribe(self.default_channel)

    def on_open(self, info):
        logger.debug("opening connection %s", info)
        #self.client.listen(self.on_chan_message)

    def on_message(self, message):
        # incoming message from client
        logger.debug("received message %s", message)

    def on_close(self):
        #self.client.unsubscribe(self.default_channel)
        pass

def main(argv=None):
    if argv is None:
        argv = sys.argv
    # currently only allow one command-line argument, the port to run on.
    logging.getLogger().setLevel(logging.DEBUG)
    port = int(argv[1]) if (len(argv) > 1) else settings.WEBSOCKET_PORT
    uri = argv[2] if len(argv) > 2 else '/sockjs'
    VcwebRouter = SockJSRouter(VcwebConnection, uri)
    app = web.Application(VcwebRouter.urls)
    logger.info("starting sockjs server [%s] on port %s", uri, port)
    app.listen(port)
    ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    sys.exit(main())


