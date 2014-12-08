import redis


class RedisPubSub(object):
    """ Singleton class for Redis Client """

    __instance = None

    @classmethod
    def get_redis_instance(cls):
        if cls.__instance is None:
            cls.__instance = redis.Redis()
        return cls.__instance

    @staticmethod
    def get_participant_broadcast_channel(experiment):
        return 'experiment_channel.{}'.format(experiment)

    @staticmethod
    def get_participant_group_channel(group):
        return 'group_channel.{}'.format(group)

    @staticmethod
    def get_experimenter_channel(experiment):
        return 'experimenter_channel.{}'.format(experiment)
