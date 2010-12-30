from django.db import models
from vcweb.core import signals


# Create your models here.
def forestry_second_tick(self):
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''


def get_resource_level(group=None):
    return group.get_data_values_by_name('resource_level') if group else None
