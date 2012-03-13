from kronos import register
from datetime import datetime
from vcweb.core import signals

@register('@hourly')
def every_hour():
    signals.hour_tick.send(sender=None, time=datetime.now())

@register('@daily')
def at_midnight():
    signals.midnight_tick.send(sender=None, time=datetime.now())

