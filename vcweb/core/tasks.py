from celery.decorators import periodic_task
from celery.schedules import crontab
from datetime import datetime, timedelta
from vcweb.core import signals

@periodic_task(run_every=timedelta(seconds=60), ignore_result=True)
def every_minute():
    '''
    Celery task invoked periodically from celerybeat.
    '''
    # use signal or just update experiment instance models directly here?
    signals.minute_tick.send(sender=None, time=datetime.now())

@periodic_task(run_every=crontab(hour="*", minute="0", day_of_week="*"))
def every_hour():
    signals.hour_tick.send(sender=None, time=datetime.now())

@periodic_task(run_every=crontab(hour="0", minute="0", day_of_week="*"))
def at_midnight():
    signals.midnight_tick.send(sender=None, time=datetime.now())

