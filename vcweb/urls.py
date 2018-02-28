
from cas import views as cas_views

from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='index.html'), name='about'),
    url(r'^contact/sent/$', TemplateView.as_view(template_name='contact_form/contact_form_sent.html'),
        name='contact_form_sent'),
    url(r'^invalid-request$', TemplateView.as_view(template_name='invalid_request.html'),
        name='invalid_request'),
    url(r'^accounts/password/reset/$', auth_views.password_reset,
        {'template_name': 'accounts/password_reset_form.html',
         'password_reset_form': PasswordResetForm}, name='password_reset'),
    url(r'^accounts/password/reset/done/$', auth_views.password_reset_done,
        {'template_name': 'accounts/password_reset_done.html'}, name='password_reset_done'),
    url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        name='password_reset_confirm'),
    url(r'^accounts/password/reset/complete/$', auth_views.password_reset_complete, name='password_reset_complete'),

    # FIXME: ideally this should be set up dynamically by iterating through each
    # ExperimentMetadata instance and using their namespace (e.g., replace all
    # instances of forestry with ExperimentMetadata.namespace)
    #    url(r'^forestry/', include('vcweb.experiment.forestry.urls', namespace='forestry', app_name='forestry')),
    #    url(r'^bound/', include('vcweb.experiment.bound.urls', namespace='bound', app_name='bound')),
    #    url(r'^lighterprints/', include('vcweb.experiment.lighterprints.urls', namespace='lighterprints',
    #                                    app_name='lighterprints')),
    #    url(r'^broker/', include('vcweb.experiment.broker.urls', namespace='broker', app_name='broker')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cas/login', cas_views.login, name='cas_login'),
    url(r'^cas/logout', cas_views.logout, name='cas_logout'),
    url(r'^cas/error', TemplateView.as_view(template_name='cas_access_forbidden.html'), name='cas_error'),
    # subject pool urls
    url(r'^subject-pool/', include('vcweb.core.subjectpool.urls',
                                   app_name='subjectpool', namespace='subjectpool')),
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
]


def experiment_urls():
    for experiment in settings.VCWEB_EXPERIMENTS:
        experiment_name = experiment.rpartition('.')[2]
# include all experiment urls.py under the experiment name's namespace
        yield url(r'^' + experiment_name + '/',
                  include(experiment + '.urls', namespace=experiment_name, app_name=experiment_name))

urlpatterns += experiment_urls()
# core urls catches everything else
urlpatterns.append(
    url(r'', include('vcweb.core.urls', namespace='core', app_name='core')))


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        url(r'^500/$', TemplateView.as_view(template_name='500.html')),
        url(r'^404/$', TemplateView.as_view(template_name='404.html')),
        url(r'^403/$', TemplateView.as_view(template_name='403.html')),
    ]
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns


