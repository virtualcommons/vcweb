from django.conf import settings


class VcwebGraphDatabase(object):

    _db = None

    @property
    def db(self):
        return self._db

    def get_db(self, data_dir=None):
        from neo4j import GraphDatabase
        if self._db is None:
            if data_dir is None:
                data_dir = settings.GRAPH_DATABASE_PATH
            self._db = GraphDatabase(data_dir)
        db = self._db
        return self._db

    def shutdown(self):
        if self._db is not None:
            self._db.shutdown()
            self._db = None

    def link(self, group, number=5):
        db = self.get_db()


_vcweb_gdb = VcwebGraphDatabase()


def get_graph_db():
    return _vcweb_gdb


def shutdown():
    _vcweb_gdb.shutdown()
