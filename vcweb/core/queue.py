import logging

from django.core import serializers

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer
from vcweb import settings
from vcweb.core.models import ChatMessage

logger = logging.getLogger(__name__)

message_exchange = Exchange("vcweb.messages", "direct", durable=True, auto_declare=True)
chat_queue = Queue("chat", exchange=message_exchange, key="chat")
experimenter_queue = Queue("experimenter", exchange=message_exchange, key="experimenter")
server_queue = Queue("server", exchange=message_exchange, key="server")
connection = BrokerConnection(settings.BROKER_HOST, settings.BROKER_USER, settings.BROKER_PASSWORD, settings.BROKER_VHOST)

channel = connection.channel()
server_consumer = Consumer(channel, server_queue)
chat_consumer = Consumer(channel, chat_queue)
# specify routing_key when you invoke producer.publish
producer = Producer(channel, exchange=message_exchange, serializer="json")

def get_channel():
    logger.debug("Trying to connect to %s vhost %s as %s with %s" %
            (settings.BROKER_HOST, settings.BROKER_VHOST, settings.BROKER_USER, settings.BROKER_PASSWORD))
    return connection.channel()

def get_chat_queue():
    return chat_queue

def get_server_queue():
    return server_queue

def get_server_consumer():
    return server_consumer

def publish(message, routing_key="server"):
    producer.publish(message, routing_key=routing_key)

def publish_chat(chat_message):
    publish(serializers.serialize("json", [chat_message]), "chat")

def broadcast_chat(experiment, message):
    logger.debug("broadcasting chat message %s for experiment %s" %
            (message, experiment))
    publish(serializers.serialize("json",
        ChatMessage.objects.message(experiment, message)), routing_key="chat")



