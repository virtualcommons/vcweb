"""
Registers django models with the django admin app.
"""

from django.contrib import admin
from django.contrib.auth.models import Permission

from vcweb.core.models import (
    Parameter, RoundParameterValue, ExperimentParameterValue, ExperimentConfiguration, RoundConfiguration,
    Experimenter, Participant, Group, Experiment, ExperimentMetadata, Address, ParticipantExperimentRelationship,
    ParticipantGroupRelationship, GroupRoundDataValue, ParticipantRoundDataValue, GroupActivityLog, ChatMessage,
    Comment, Like, OstromlabFaqEntry, ParticipantSignup, Invitation, ExperimentSession
)


models = (
    Parameter, RoundParameterValue, ExperimentParameterValue, ExperimentConfiguration, RoundConfiguration,
    Experimenter, Participant, Group, Experiment, ExperimentMetadata, Address, ParticipantExperimentRelationship,
    ParticipantGroupRelationship, GroupRoundDataValue, ParticipantRoundDataValue, GroupActivityLog, ChatMessage,
    Comment, Like, OstromlabFaqEntry, ParticipantSignup, Invitation, ExperimentSession
)
for model in models:
    admin.site.register(model)
admin.site.register(Permission)
