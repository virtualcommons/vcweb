'''
The updater module is invoked periodically from an external process to set up the signaling and timing / processing
of experiments in progress.

@author: alllee
'''

from vcweb.core.models import GameInstance
from vcweb.core import signals

from datetime import datetime

class GameMonitor():
    @classmethod
    def update(cls):
        now = datetime.now()
        print "Sending second tick signal at %s" % now
        print ["\n\t" + gameInstance + "\n" for gameInstance in GameInstance.objects.get_all_active()]
        signals.second_tick.send(sender=cls, now)

