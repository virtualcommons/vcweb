from datetime import datetime
import logging

from kronos import register

from . import signals
from .decorators import log_signal_errors


logger = logging.getLogger(__name__)


@register('0 0 * * *')
@log_signal_errors
def system_daily_tick():
    return signals.system_daily_tick.send_robust(sender=None, time=datetime.now())


@register('0 0 * * 0')
@log_signal_errors
def system_weekly_tick():
    return signals.system_weekly_tick.send_robust(sender=None, time=datetime.now())


@register('0 0 1 * *')
@log_signal_errors
def system_monthly_tick():
    return signals.system_monthly_tick.send_robust(sender=None, time=datetime.now())


#@register('@weekly')
# def refresh_foursquare_categories():
#    fetch_foursquare_categories(refresh=True)
