'''
registering django models with django admin
'''

from django.contrib import admin
from vcweb.core.models import *

admin.site.register(DataParameter)
admin.site.register(RoundParameter)
admin.site.register(ConfigurationParameter)
admin.site.register(ExperimentConfiguration)
admin.site.register(RoundConfiguration)
admin.site.register(Experimenter)
admin.site.register(Participant)
admin.site.register(Group)
admin.site.register(Experiment)
admin.site.register(ParticipantExperimentRelationship)
admin.site.register(ParticipantGroupRelationship)
