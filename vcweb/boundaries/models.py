from django.db import models
from vcweb.core import simplecache
from vcweb.core.services import ExperimentService

# Create your models here.

@simplecache
def get_experiment_metadata_name():
    return 'bound'



