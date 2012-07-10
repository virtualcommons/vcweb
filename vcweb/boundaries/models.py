from django.db import models
from vcweb.core import simplecache
from vcweb.core.services import ExperimentService

# Create your models here.

class BoundariesExperimentService(ExperimentService):
    @simplecache
    def get_experiment_metadata_name():
        return 'bound'

