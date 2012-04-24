from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin
from django.views.decorators.cache import cache_page
from vcweb import settings
from vcweb.core import views

from django.views.generic.base import TemplateView
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from dajaxice.core import dajaxice_autodiscover
# set up dajaxice URLs
dajaxice_autodiscover()
# set up admin URLs
admin.autodiscover()

handler500 = views.handler500

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),
    url(r'^contact/$', cache_page(60*15)(TemplateView.as_view(template_name='contact.html')), name='contact'),
    # FIXME: customize password reset email and forms to not go through django admin?
    #url(r'^accounts/password_reset/$', 'django.contrib.auth.views.password_reset', {'template_name':'password_reset_form.html', 'email_template_name':'userpanel/password_reset_email.html'}),
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset', name='password-reset'),
    url(r'^accounts/password_reset/done/$', 'django.contrib.auth.views.password_reset_done'),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    url(r'^accounts/reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
    url(r'^%s/' % settings.DAJAXICE_MEDIA_PREFIX, include('dajaxice.urls')),

    # FIXME: ideally this should be set up dynamically by iterating through each
    # ExperimentMetadata instance and using their namespace (e.g., replace all
    # instances of forestry with ExperimentMetadata.namespace)
    url(r'^forestry/', include('vcweb.forestry.urls', namespace='forestry', app_name='forestry')),
    url(r'^sanitation/', include('vcweb.sanitation.urls', namespace='sanitation', app_name='sanitation')),
    url(r'^lighterprints/', include('vcweb.lighterprints.urls', namespace='lighterprints', app_name='lighterprints')),
    url(r'^admin/', include(admin.site.urls)),
    # social auth urls for logging in via fb, google, foursquare, etc.
    url(r'', include('social_auth.urls')),
    # core catches everything else
    url(r'', include('vcweb.core.urls', namespace='core', app_name='core')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
