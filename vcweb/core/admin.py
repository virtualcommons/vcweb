'''
Registers django models with the django admin app.
'''

from django.contrib import admin
from django.contrib.auth.models import Permission
from vcweb.core.models import *


models = (
        Parameter, RoundParameterValue, ExperimentConfiguration, RoundConfiguration,
        Experimenter, Participant, Group, Experiment,
        ParticipantExperimentRelationship, ParticipantGroupRelationship,
        GroupRoundDataValue, ParticipantRoundDataValue, GroupActivityLog,
        ChatMessage, QuizQuestion, Comment, Like
        )

for model in models:
    admin.site.register(model)

admin.site.register(Permission)
