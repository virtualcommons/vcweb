from django.conf.urls.defaults import *
from django.contrib import admin
import settings


# FIXME: needed?
#import settings (r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.BASE_DIR+'/core/static/', 'show_indexes': True})
# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'django.views.generic.simple.direct_to_template', {'template':'index.html'}, name='home'),
    url(r'^about/$', 'django.views.generic.simple.direct_to_template', {'template':'about.html'}, name='about'),
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset', name='password-reset'),
    url(r'^accounts/password_reset/$', 'django.contrib.auth.views.password_reset', {'template_name':'password_reset_form.html', 'email_template_name':'userpanel/password_reset_email.html'}),
    url(r'^accounts/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', {'template_name':'password_reset_done.html'}),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'password_reset_confirm.html'}),
    url(r'^accounts/reset/done/$', 'django.contrib.auth.views.password_reset_complete', {'template_name':'password_reset_complete.html'}),

    url(r'^forestry/', include('forestry.urls', namespace='forestry', app_name='forestry')),
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

