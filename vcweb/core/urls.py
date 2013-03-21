from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required
from vcweb import settings
from vcweb.core.views import (Dashboard, LoginView, LogoutView, RegistrationView, monitor, CloneExperimentView,
        RegisterEmailListView, RegisterSimpleParticipantsView, ClearParticipantsExperimentView, add_experiment,
        Participate, download_data, export_configuration, api_logger, participant_ready, deactivate)
import logging
import urllib

logger = logging.getLogger(__name__)
'''
URLs for the core vcweb app
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'^dashboard/?$', login_required(Dashboard.as_view()), name='dashboard'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', login_required(LogoutView.as_view()), name='logout'),
    url(r'^accounts/add/$', RegistrationView.as_view(), name='register'),
    url(r'^accounts/profile/$', 'account_profile', name='profile'),
    url(r'^participate/?$', Participate.as_view(), name='participate'),
    url(r'^participate/(?P<namespace>\w+)/instructions', 'instructions', name='namespace_instructions'),
    url(r'^experiment/add$', add_experiment, name='add_experiment'),
    url(r'^experiment/participant-ready$', participant_ready, name='participant_ready'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', monitor, name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/register-email-list$', RegisterEmailListView.as_view(), name='register_email_list'),
    url(r'^experiment/(?P<pk>\d+)/register-simple$', RegisterSimpleParticipantsView.as_view(), name='register_simple'),
    # FIXME: refactor these into POSTs using the ExperimentActionForm
    url(r'^experiment/(?P<pk>\d+)/deactivate$', deactivate, name='deactivate'),
    url(r'^experiment/(?P<pk>\d+)/clone$', CloneExperimentView.as_view(), name='clone'),
    url(r'^experiment/(?P<pk>\d+)/clear-participants', ClearParticipantsExperimentView.as_view(), name='clear_participants'),
#    url(r'^experiment/(?P<pk>\d+)/add-participants/(?P<count>[\d]+)$', 'add_participants', name='add_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', download_data, name='download_data'),
    url(r'^experiment/(?P<pk>\d+)/export/configuration(?P<file_extension>.[\w]+)$', export_configuration, name='export_configuration'),
# experiment controller actions are the most general, needs to be matched at the very end
    # deliberately match any prefix to api/2525/log
    url(r'api/log/(?P<participant_group_id>\d+)$', api_logger, name='api-logger'),
    )

def foursquare_auth_dict(**kwargs):
    return dict(kwargs, client_id=settings.FOURSQUARE_CONSUMER_KEY, client_secret=settings.FOURSQUARE_CONSUMER_SECRET, v=settings.FOURSQUARE_CONSUMER_DATE_VERIFIED)

def foursquare_url(url, **kwargs):
    url = "%s?%s" % (url, urllib.urlencode(foursquare_auth_dict(**kwargs)))
    logger.debug("%s", url)
    return url

def foursquare_venue_search_url(**kwargs):
    return foursquare_url(settings.FOURSQUARE_VENUE_SEARCH_ENDPOINT, **kwargs)

def foursquare_categories_url(**kwargs):
    return foursquare_url(settings.FOURSQUARE_CATEGORIES_ENDPOINT, **kwargs)


