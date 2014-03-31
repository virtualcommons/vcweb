from datetime import datetime
from functools import wraps
from kronos import register
from vcweb.core import signals

import logging

logger = logging.getLogger(__name__)


def log_signal_errors(signal_sender):
    @wraps(signal_sender)
    def error_checker():
        results = signal_sender()
        for receiver, response in results:
            if response is not None:
                logger.error("errors while dispatching to %s: %s", receiver, response)
    return error_checker

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
#def refresh_foursquare_categories():
#    fetch_foursquare_categories(refresh=True)
