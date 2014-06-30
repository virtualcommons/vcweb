from neo4j import GraphDatabase
from django.conf import settings


class VcwebGraphDatabase(object):
    _db = None

    def create_db(self, data_dir):
        if self._db is None:
            self._db = GraphDatabase(data_dir)
        return self._db

    def shutdown(self):
        if self._db is not None:
            self._db.shutdown()
            self._db = None


_vcweb_gdb = VcwebGraphDatabase()


def get_graph_db(data_dir=None):
    if data_dir is None:
        data_dir = settings.GRAPH_DATABASE_PATH
    return _vcweb_gdb.create_db(data_dir)


def shutdown():
    _vcweb_gdb.shutdown()
