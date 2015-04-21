from django.core import management
from django.dispatch import receiver
from datetime import datetime
from kronos import register

from . import signals
from .decorators import log_signal_errors
from .models import get_audit_data

import logging
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


@receiver(signals.system_weekly_tick, dispatch_uid='schedule-weekly-tasks')
def weekly_schedule_tasks(sender, start=None, **kwargs):
    email = create_markdown_email(template="email/weekly-audit-email.txt", context=get_audit_data(),
                                  subject="VCWEB Audit", to_email=[settings.DEFAULT_EMAIL])
    email.send()

@receiver(signals.system_monthly_tick, dispatch_uid='schedule-monthly-tasks')
def validate_class_status(sender, start=None, **kwargs):
    management.call_command('validate_student_class_status')


#@register('@weekly')
# def refresh_foursquare_categories():
#    fetch_foursquare_categories(refresh=True)
