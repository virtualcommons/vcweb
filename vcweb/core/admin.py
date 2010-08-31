'''
Created on Jul 8, 2010

@author: alllee
'''

from Canvas import Group
from django.contrib import admin
from vcweb.core.models import DataParameter, RoundParameter, GameConfiguration, \
    RoundConfiguration, Experimenter, Participant, GameInstance, ParticipantGroup

admin.site.register(DataParameter)
admin.site.register(RoundParameter)
admin.site.register(GameConfiguration)
admin.site.register(RoundConfiguration)
admin.site.register(Experimenter)
admin.site.register(Participant)
admin.site.register(Group)
admin.site.register(GameInstance)
admin.site.register(ParticipantGroup)
