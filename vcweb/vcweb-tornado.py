#!/usr/bin/env python

import tornado.web
from tornad_io import SocketIOHandler
from tornad_io import SocketIOServer

import os
import sys

sys.path.append(os.path.abspath('..'))

os.environ['DJANGO_SETTINGS_MODULE'] = 'vcweb.settings'
from vcweb.core.models import *

import logging

logger = logging.getLogger('vcweb.tornad.io')



participants = set()

'''
currently unused, would it be useful to dangle some handlers on specific
tornado-handled URLs to return JSON objs, i.e., handled outside of Django?
'''
class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render("index.html")

class ChatHandler(SocketIOHandler):
    """Socket.IO handler"""

    def on_open(self, *args, **kwargs):
        ''' parse args / kwargs for participant session info so we know which group
        to route this guy to
        '''

        logger.debug("args are: %s" % str(args))
        logger.debug("kwargs are: %s" % str(kwargs))

        self.send("Welcome!")
        participants.add(self)

    def on_message(self, message):
        ''' message should be a fully parsed Python object from the incoming JSON '''
        for p in participants:
            p.send(message)

    def on_close(self):
        participants.remove(self)
        for p in participants:
            p.send("A user has left.")

#use the routes classmethod to build the correct resource
defaultRoute = ChatHandler.routes("socket.io/*")

#configure the Tornado application
application = tornado.web.Application(
    [(r'/', IndexHandler), defaultRoute], 
    enabled_protocols = ['websocket', 'flashsocket', 'xhr-multipart', 'xhr-polling', 'jsonp-polling'],
    flash_policy_port = 8043,
    socket_io_port = 8888
)

if __name__ == "__main__":
    socketio_server = SocketIOServer(application) #spin up the server
