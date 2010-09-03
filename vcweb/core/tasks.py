'''
The updater module is invoked periodically from an external process to set up the signaling and timing / processing
of experiments in progress.

@author: alllee
'''

from celery.decorators import periodic_task
from datetime import datetime, timedelta
from vcweb.core import signals


@periodic_task(run_every=timedelta(seconds=1), ignore_result=True)
def every_second():
    # use signal or just update experiment instance models directly here?
    signals.second_tick.send(sender=None, time=datetime.now())



