from kronos import register
from datetime import datetime
from vcweb.core import signals

#@register('@minute')
#def every_minute():
#    signals.minute_tick.send(sender=None, time=datetime.now())

#@register('@hourly')
#def every_hour():
#    signals.hour_tick.send(sender=None, time=datetime.now())

@register('1 0 * * *')
def pre_system_daily_tick():
    signals.pre_system_daily_tick.send(sender=None, time=datetime.now())


@register('2 0 * * *')
def system_daily_tick():
    signals.system_daily_tick.send(sender=None, time=datetime.now())

@register('3 0 * * *')
def post_system_daily_tick():
    signals.post_system_daily_tick.send(sender=None, time=datetime.now())

#@register('@weekly')
#def refresh_foursquare_categories():
#    fetch_foursquare_categories(refresh=True)
