from django.db import models
from vcweb.core import simplecache
from vcweb.core.models import ExperimentMetadata


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='bound')



