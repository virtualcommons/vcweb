from django.db import models
from vcweb.core.signals import *
import threading

# Create your models here.



def forestry_second_tick(self):
    print "Monitoring Forestry Game Instances."
    '''
    check all forestry game instances
    '''

def start_monitor_thread(sender, **kwargs):
    t = threading.Thread(target=forestry_second_tick, kwargs)
    t.setDaemon(True)
    t.start()


second_tick.connect(start_monitor_thread, sender=None)


