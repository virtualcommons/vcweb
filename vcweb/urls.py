import autocomplete_light
# import every app/autocomplete_light_registry.py FIXME: can probably
# remove for Django 1.7
autocomplete_light.autodiscover()
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView

urlpatterns = [
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='home'),
    url(r'^about/$', TemplateView.as_view(template_name='about.html'),
        name='about'),
    url(r'^contact/', include('contact_form.urls')),
    url(r'^invalid-request$', TemplateView.as_view(template_name='invalid_request.html'),
        name='invalid_request'),
    url(r'^accounts/password/reset/$', auth_views.password_reset,
        {'template_name': 'account/password_reset_form.html',
         'password_reset_form': PasswordResetForm}, name='password_reset'),
    url(r'^accounts/password/reset/done/$', auth_views.password_reset_done,
        {'template_name': 'account/password_reset_done.html'}, name='password_reset_done'),
    url(r'^accounts/password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^accounts/password/reset/complete/$', auth_views.password_reset_complete,
        name='password_reset_complete'),

    # FIXME: ideally this should be set up dynamically by iterating through each
    # ExperimentMetadata instance and using their namespace (e.g., replace all
    # instances of forestry with ExperimentMetadata.namespace)
    #    url(r'^forestry/', include('vcweb.experiment.forestry.urls', namespace='forestry', app_name='forestry')),
    #    url(r'^bound/', include('vcweb.experiment.bound.urls', namespace='bound', app_name='bound')),
    #    url(r'^lighterprints/', include('vcweb.experiment.lighterprints.urls', namespace='lighterprints',
    #                                    app_name='lighterprints')),
    #    url(r'^broker/', include('vcweb.experiment.broker.urls', namespace='broker', app_name='broker')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^cas/login', 'cas.views.login'),
    url(r'^cas/logout', 'cas.views.logout'),
    url(r'^cas/error', TemplateView.as_view(template_name='cas_access_forbidden.html'),
        name='cas_error'),  # core catches everything else
    # subject pool urls
    url(r'^subject-pool/', include('vcweb.core.subjectpool.urls',
                                   app_name='subjectpool', namespace='subjectpool')),
    # Uncomment the admin/doc line below and add 'django.contrib.admindocs'
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),
]


def experiment_urls():
    # crude filter, if 'experiment' is in the app_name, include it
    for experiment in settings.EXPERIMENTS:
        experiment_name = experiment.rpartition('.')[2]
# include all experiment urls.py under the experiment name's namespace
        yield url(r'^' + experiment_name + '/',
                  include(experiment + '.urls',
                          namespace=experiment_name,
                          app_name=experiment_name))

urlpatterns += experiment_urls()
# core urls catches everything else
urlpatterns.append(url(r'', include('vcweb.core.urls', namespace='core', app_name='core')))


if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [
        url(r'^500/$', TemplateView.as_view(template_name='500.html')),
        url(r'^404/$', TemplateView.as_view(template_name='404.html')),
        url(r'^403/$', TemplateView.as_view(template_name='403.html')),
    ]
