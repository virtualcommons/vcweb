'''
registering django models with django admin
'''
from django.contrib import admin
from vcweb.lighterprints.models import Activity

admin.site.register(Activity)
