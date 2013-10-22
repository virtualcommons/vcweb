import autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()
from django.conf.urls.defaults import patterns, url, include
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.decorators.cache import cache_page
from django.views.generic.base import TemplateView

from vcweb import settings
from django.contrib.auth.forms import PasswordResetForm

from dajaxice.core import dajaxice_autodiscover, dajaxice_config
# set up dajaxice URLs
dajaxice_autodiscover()
# set up admin URLs
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),
    url(r'^contact/$', cache_page(60*15)(TemplateView.as_view(template_name='contact.html')), name='contact'),
    # FIXME: customize password reset email and forms to not go through django admin?
    #url(r'^accounts/password_reset/$', 'django.contrib.auth.views.password_reset', {'template_name':'password_reset_form.html', 'email_template_name':'userpanel/password_reset_email.html'}),
    url(r'^accounts/password/reset/$', 'django.contrib.auth.views.password_reset', { 'template_name': 'account/password_reset_form.html', 'password_reset_form': PasswordResetForm}, name='password-reset'),
    url(r'^accounts/password_reset/done/$', 'django.contrib.auth.views.password_reset_done', { 'template_name': 'account/password_reset_done.html' }),
    url(r'^accounts/reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'django.contrib.auth.views.password_reset_confirm'),
    url(r'^accounts/reset/done/$', 'django.contrib.auth.views.password_reset_complete'),
# dajaxice core
    url(dajaxice_config.dajaxice_url, include('dajaxice.urls')),

    # FIXME: ideally this should be set up dynamically by iterating through each
    # ExperimentMetadata instance and using their namespace (e.g., replace all
    # instances of forestry with ExperimentMetadata.namespace)
    url(r'^forestry/', include('vcweb.forestry.urls', namespace='forestry', app_name='forestry')),
    url(r'^bound/', include('vcweb.bound.urls', namespace='bound', app_name='bound')),
    url(r'^lighterprints/', include('vcweb.lighterprints.urls', namespace='lighterprints', app_name='lighterprints')),
    url(r'^broker/', include('vcweb.broker.urls', namespace='broker', app_name='broker')),
    url(r'^subject-pool/', include('vcweb.subject_pool.urls', namespace='subject-pool', app_name='subject-pool')),
    url(r'^admin/', include(admin.site.urls)),
    # social auth urls for logging in via fb, google, foursquare, etc.
    url(r'', include('social_auth.urls')),
    # core catches everything else
    url(r'', include('vcweb.core.urls', namespace='core', app_name='core')),
    url(r'^autocomplete/', include('autocomplete_light.urls')),


    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

handler500 = 'vcweb.core.views.handler500'

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

