from django.db import models

from vcweb.core import simplecache
from vcweb.core.models import Parameter
from vcweb.forestry.models import get_harvest_decision_parameter

def get_max_harvest_hours(experiment):
    return experiment.experiment_configuration.get_parameter_value(name='max_harvest_hours', default=10).int_value

# FIXME: this is currently broken
@simplecache
def get_conservation_hours_parameter():
    return Parameter.objects.get(name='conservation_hours')

