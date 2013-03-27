from kronos import register
from datetime import datetime
from vcweb.core import signals
from vcweb.core.services import fetch_foursquare_categories

@register('@minute')
def every_minute():
    signals.minute_tick.send(sender=None, time=datetime.now())

@register('@hourly')
def every_hour():
    signals.hour_tick.send(sender=None, time=datetime.now())

@register('@daily')
def at_midnight():
    signals.midnight_tick.send(sender=None, time=datetime.now())

@register('@weekly')
def refresh_foursquare_categories():
    fetch_foursquare_categories(refresh=True)
