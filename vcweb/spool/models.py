from django.db import models
from vcweb.core.models import (User, Participant, Experiment)


class ExperimentSession(models.Model):
    experiment = models.ForeignKey(Experiment)
    date_created = models.DateTimeField(auto_now_add=True)
    scheduled_date = models.DateTimeField()
    scheduled_end_date = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(default=20)
    creator = models.ForeignKey(User)

class Invitation(models.Model):
    participant = models.ForeignKey(Participant)
    experiment_session = models.ForeignKey(ExperimentSession)
    date_created = models.DateTimeField(auto_now_add=True)
    sender = models.ForeignKey(User)

class ParticipantSignup(models.Model):
    participant = models.ForeignKey(Participant, related_name='signup_set')
    invitation = models.ForeignKey(Invitation, related_name='signup_set')
    date_created = models.DateTimeField(auto_now_add=True)
    attendance = models.CharField(max_length=1, null=True, blank=True, choices=((0, 'participated'), (1, 'turned away'), (2, 'absent')))

class FaqEntry(models.Model):
    creator = models.ForeignKey(User)
    date_created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    question = models.TextField()
    answer = models.TextField()
    slug = models.SlugField(max_length=32)

class ParticipantStatistics(models.Model):
    participant = models.ForeignKey(Participant, related_name='statistics_set')
    absences = models.PositiveIntegerField(default=0)
    discharges = models.PositiveIntegerField(default=0)
    participations = models.PositiveIntegerField(default=0)
