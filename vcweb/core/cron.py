from datetime import datetime
import logging

from kronos import register

from . import signals
from .decorators import log_signal_errors


logger = logging.getLogger(__name__)


@register('0 0 * * *')
@log_signal_errors
def pre_system_daily_tick():
    return signals.pre_system_daily_tick.send_robust(sender=None, time=datetime.now())


@register('1 0 * * *')
@log_signal_errors
def system_daily_tick():
    return signals.system_daily_tick.send_robust(sender=None, time=datetime.now())


@register('2 0 * * *')
@log_signal_errors
def post_system_daily_tick():
    return signals.post_system_daily_tick.send_robust(sender=None, time=datetime.now())

#@register('@weekly')
# def refresh_foursquare_categories():
#    fetch_foursquare_categories(refresh=True)
