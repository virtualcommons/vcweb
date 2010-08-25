'''
The updater module is invoked periodically from an external process to set up the signaling and timing / processing
of experiments in progress.

@author: alllee
'''

from vcweb.core.models import GameInstance
from vcweb.core import signals

from datetime import datetime

def second_tick_handler(sender, **kwargs):
    print "handling second tick signal."

signals.second_tick.connect(second_tick_handler)

