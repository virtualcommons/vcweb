from django.db import models
from vcweb.core.signals import *
import threading

# Create your models here.



def forestry_second_tick(self):
    print "Monitoring Forestry Game Instances."
    '''
    check all forestry game instances
    '''
