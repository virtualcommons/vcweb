import redis

from django.conf import settings


class RedisPubSub(object):
    """ Singleton class for Redis Client """

    __instance = None

    @classmethod
    def get_redis_instance(cls):
        if cls.__instance is None:
            cls.__instance = redis.Redis(host=settings.REDIS_HOST)
        return cls.__instance

    @staticmethod
    def get_participant_broadcast_channel(experiment_pk):
        return 'experiment_channel.{}'.format(experiment_pk)

    @staticmethod
    def get_participant_group_channel(group_pk):
        return 'group_channel.{}'.format(group_pk)

    @staticmethod
    def get_experimenter_channel(experiment_pk):
        return 'experimenter_channel.{}'.format(experiment_pk)
