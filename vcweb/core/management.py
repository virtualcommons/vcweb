from django.db.models import signals
from django.dispatch import receiver

#from vcweb.core.graph import dao
import vcweb

import logging
logger = logging.getLogger(__name__)


''' disabled for the time being, is a large maintenance burden to have to set up python-jpype and the JVM'''
# FIXME: move to lighterprints app instead if we depend on lighterprints models syncdb
''' create graph database indexes '''
#@receiver(signals.post_syncdb, sender=vcweb.lighterprints.models, dispatch_uid='graph-database-index-creator')
#def create_indexes(sender, **kwargs):
#    dao.initialize_indexes()

