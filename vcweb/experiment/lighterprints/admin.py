'''
registering django models with django admin
'''
from django.contrib import admin

from vcweb.experiment.lighterprints.models import Activity, ActivityAvailability


admin.site.register(Activity)
admin.site.register(ActivityAvailability)
