import autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView

from django.contrib.auth.forms import PasswordResetForm

# set up admin URLs
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),
    url(r'^contact/$', TemplateView.as_view(template_name='contact.html'), name='contact'),
    url(r'^invalid-request$', TemplateView.as_view(template_name='invalid_request.html'), name='invalid_request'),
    # FIXME: customize password reset email and forms to not go through django admin?
    #url(r'^accounts/password_reset/$', 'django.contrib.auth.views.password_reset', {'template_name':'password_reset_form.html', 'email_template_name':'userpanel/password_reset_email.html'}),
    url(r'^accounts/password/reset/$', auth_views.password_reset, { 'template_name': 'account/password_reset_form.html', 'password_reset_form': PasswordResetForm}, name='password_reset'),
    url(r'^accounts/password/reset/done/$', auth_views.password_reset_done, { 'template_name': 'account/password_reset_done.html' }, name='password_reset_done'),
    url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^accounts/password/reset/complete/$', auth_views.password_reset_complete, name='password_reset_complete'),

    # FIXME: ideally this should be set up dynamically by iterating through each
    # ExperimentMetadata instance and using their namespace (e.g., replace all
    # instances of forestry with ExperimentMetadata.namespace)
    url(r'^forestry/', include('vcweb.forestry.urls', namespace='forestry', app_name='forestry')),
    url(r'^bound/', include('vcweb.bound.urls', namespace='bound', app_name='bound')),
    url(r'^lighterprints/', include('vcweb.lighterprints.urls', namespace='lighterprints', app_name='lighterprints')),
    url(r'^broker/', include('vcweb.broker.urls', namespace='broker', app_name='broker')),
    url(r'^subject-pool/', include('vcweb.subject_pool.urls', namespace='subject_pool', app_name='subject_pool')),
    url(r'^admin/', include(admin.site.urls)),
    # core catches everything else
    url(r'', include('vcweb.core.urls', namespace='core', app_name='core')),
    url(r'^autocomplete/', include('autocomplete_light.urls')),

    url(r'^cas/login', 'cas.views.login'),
    url(r'^cas/logout', 'cas.views.logout'),
    url(r'^cas/error', TemplateView.as_view(template_name='cas_access_forbidden.html'), name='cas_error'),
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
)

handler500 = 'vcweb.core.views.handler500'

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

