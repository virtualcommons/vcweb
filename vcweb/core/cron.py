import logging
from datetime import datetime

from django.conf import settings
from django.core import management
from django.dispatch import receiver

from . import signals
from .decorators import log_signal_errors
from .models import get_audit_data, create_markdown_email

logger = logging.getLogger(__name__)



@log_signal_errors
def system_daily_tick():
    return signals.system_daily_tick.send_robust(sender=None, time=datetime.now())


@log_signal_errors
def system_weekly_tick():
    return signals.system_weekly_tick.send_robust(sender=None, time=datetime.now())


@log_signal_errors
def system_monthly_tick():
    return signals.system_monthly_tick.send_robust(sender=None, time=datetime.now())


@receiver(signals.system_weekly_tick, dispatch_uid='schedule-weekly-tasks')
def run_weekly_audit(sender, start=None, **kwargs):
    email = create_markdown_email(template="email/weekly-audit-email.txt", context=get_audit_data(),
                                  subject="VCWEB Audit", to_email=[settings.DEFAULT_EMAIL])
    email.send()


@receiver(signals.system_monthly_tick, dispatch_uid='schedule-monthly-tasks')
def validate_class_status(sender, start=None, **kwargs):
    management.call_command('validate_student_class_status')
