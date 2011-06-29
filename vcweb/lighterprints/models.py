from django.db import models

class Activity(models.Model):
    name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=256)
    description = models.TextField()
    url = models.URLField()
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    available_all_day = models.BooleanField(default=False)
# FIXME: allow for experiment-configurable levels?
    level = models.PositiveIntegerField(default=1)
    group_activity = models.BooleanField(default=False, help_text='Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')
    cooldown = models.PositiveIntegerField(default=1, help_text='How much time, in hours, must elapse before this activity can become available again')

    @property
    def label(self):
        return self.display_name if self.display_name else self.name

    @property
    def icon_name(self):
        return self.name

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.savings)

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity)
    available_start_time = models.TimeField(null=True, blank=True)
    available_end_time = models.TimeField(null=True, blank=True)
