'''
Created on Jul 8, 2010

@author: alllee
'''

from django.contrib import admin
from vcweb.core.models import *

admin.site.register(GameMetadata)
admin.site.register(DataParameter)
admin.site.register(RoundParameter)
admin.site.register(GameConfiguration)
admin.site.register(RoundConfiguration)
admin.site.register(Experimenter)
admin.site.register(Participant)
admin.site.register(Group)
admin.site.register(GameInstance)

