from django.conf.urls.defaults import *

import settings

# FIXME: needed?
#import settings (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.BASE_DIR+'/core/static/', 'show_indexes': True})
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.simple.direct_to_template', {'template':'index.html'}, name='home'),
    url(r'^about/$', 'django.views.generic.simple.direct_to_template', {'template':'about.html'}, name='about'),
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset', name='password-reset'),
    url(r'^forestry/', include('vcweb.forestry.urls', namespace='forestry', app_name='forestry')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('vcweb.core.urls', namespace='core', app_name='vcweb')),
    # make sure this is last


    # Example:
    # (r'^vcweb/', include('vcweb.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)/$', 'django.views.static.serve',
         {'document_root': settings.STATIC_BASE_DIR, 'show_indexes': True}
         ),

        )

