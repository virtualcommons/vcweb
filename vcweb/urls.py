from django.conf.urls.defaults import *
from django.contrib import admin
from vcweb import settings

from django.views.generic.simple import direct_to_template

from dajaxice.core import dajaxice_autodiscover
# set up dajaxice URLs
dajaxice_autodiscover()
# set up admin URLs
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template':'index.html'}, name='home'),
    url(r'^about/$', direct_to_template, {'template':'about.html'}, name='about'),
    url(r'^contact/$', direct_to_template, {'template':'contact.html'}, name='contact'),
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset', name='password-reset'),
    url(r'^accounts/password_reset/$', 'django.contrib.auth.views.password_reset', {'template_name':'password_reset_form.html', 'email_template_name':'userpanel/password_reset_email.html'}),
    url(r'^accounts/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', {'template_name':'password_reset_done.html'}),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm', {'template_name':'password_reset_confirm.html'}),
    url(r'^accounts/reset/done/$', 'django.contrib.auth.views.password_reset_complete', {'template_name':'password_reset_complete.html'}),
    url(r'^%s/' % settings.DAJAXICE_MEDIA_PREFIX, include('dajaxice.urls')),

    # FIXME: figure out if we can dynamically include every custom app's
    # urlconf
    url(r'^forestry/', include('vcweb.forestry.urls', namespace='forestry', app_name='forestry')),
    url(r'^admin/', include(admin.site.urls)),
    # core catches everything else
    url(r'', include('vcweb.core.urls', namespace='core', app_name='core')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)/$', 'django.views.static.serve',
         {'document_root': settings.STATIC_BASE_DIR, 'show_indexes': True}
         ),

        )

