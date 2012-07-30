from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page
from vcweb import settings
from vcweb.core.views import (Dashboard, LoginView, LogoutView, RegistrationView, MonitorExperimentView, CloneExperimentView,
        RegisterEmailListView, RegisterSimpleParticipantsView, ClearParticipantsExperimentView, add_experiment,
        download_data, experiment_controller, api_logger)

import logging
import urllib

logger = logging.getLogger(__name__)
'''
URLs defined by the core vcweb app.
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'^dashboard/?$', login_required(Dashboard.as_view()), name='dashboard'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', login_required(LogoutView.as_view()), name='logout'),
    url(r'^accounts/add/$', RegistrationView.as_view(), name='register'),
    url(r'^accounts/profile/$', 'account_profile', name='profile'),
    url(r'^participate/(?P<namespace>\w+)/instructions', 'instructions', name='namespace_instructions'),
    url(r'^experiment/add$', add_experiment, name='add_experiment'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', cache_page(60)(MonitorExperimentView.as_view()), name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/register-email-list$', RegisterEmailListView.as_view(), name='register_email_list'),
    url(r'^experiment/(?P<pk>\d+)/register-simple$', RegisterSimpleParticipantsView.as_view(), name='register_simple'),
    url(r'^experiment/(?P<pk>\d+)/clone$', CloneExperimentView.as_view(), name='clone'),
    url(r'^experiment/(?P<pk>\d+)/clear-participants', ClearParticipantsExperimentView.as_view(), name='clear_participants'),
#    url(r'^experiment/(?P<pk>\d+)/add-participants/(?P<count>[\d]+)$', 'add_participants', name='add_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', download_data, name='download_data'),
# experiment controller actions are the most general, needs to be matched at the very end
    url(r'^experiment/(?P<pk>\d+)/(?P<experiment_action>[\w-]+)$', experiment_controller, name='experiment_controller'),
    # deliberately match any prefix to api/2525/log
    url(r'api/log/(?P<participant_group_id>\d+)$', api_logger, name='api-logger'),
    )
# add ajax actions
urlpatterns += patterns('vcweb.core.ajax',
    url(r'^ajax/(?P<pk>\d+)/(<?P<experiment_action[\w-]+)$', 'experiment_controller'),
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


