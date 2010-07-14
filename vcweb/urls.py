from django.conf.urls.defaults import *

import settings

# FIXME: needed?
#import settings (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.BASE_DIR+'/core/static/', 'show_indexes': True})
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',                   
    (r'^admin/', include(admin.site.urls)),
    
    (r'^games/$', 'vcweb.core.views.home'),
    (r'^games/list/$', 'vcweb.core.views.list'),
    (r'^games/config/$', 'vcweb.core.views.config'),
    (r'^static/(?P<path>.*)/$', 'django.views.static.serve', {'document_root': settings.BASE_DIR, 'show_indexes': True})
                           
    # Example:
    # (r'^vcweb/', include('vcweb.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)
