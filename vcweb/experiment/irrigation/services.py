import sys

from vcweb.core import simplecache
from vcweb.core.models import ExperimentMetadata

EXPERIMENT_METADATA_NAME = sys.intern('irrigation')


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace=EXPERIMENT_METADATA_NAME)
