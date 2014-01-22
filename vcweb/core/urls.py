from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from vcweb import settings
from vcweb.core.ajax import (get_round_data, save_experimenter_notes, experiment_controller, create_experiment,
        clone_experiment, archive,
        )
from vcweb.core.views import (dashboard, LoginView, LogoutView, RegistrationView, monitor,
        RegisterEmailListView, RegisterTestParticipantsView, completed_survey, toggle_bookmark_experiment_metadata,
        check_survey_completed, Participate, download_data, export_configuration, api_logger, participant_api_login,
        api_logout, participant_ready, check_ready_participants, get_dashboard_view_model,
        edit_experiment_configuration, clone_experiment_configuration)
import logging
import urllib

logger = logging.getLogger(__name__)
'''
URLs for the core vcweb app
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'^dashboard/?$', dashboard, name='dashboard'),
    url(r'^participant/session/?$', 'get_participant_sessions', name='participant_sessions'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', login_required(LogoutView.as_view()), name='logout'),
    #url(r'^accounts/add/$', RegistrationView.as_view(), name='register'),
    url(r'^accounts/profile/$', 'account_profile', name='profile'),
    url(r'^accounts/profile/update$', 'update_account_profile', name='update_profile'),
    url(r'^accounts/check-email$', 'check_user_email', name='check_email'),
    url(r'^participate/?$', Participate.as_view(), name='participate'),
    url(r'^participate/survey-completed', completed_survey, name='survey_completed'),
    url(r'^participate/(?P<pk>\d+)/check-survey-completed', check_survey_completed, name='check_survey_completed'),
    url(r'^experiment/participant-ready$', participant_ready, name='participant_ready'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', monitor, name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/register-email-list$', RegisterEmailListView.as_view(), name='register_email_list'),
    url(r'^experiment/(?P<pk>\d+)/register-test-participants$', RegisterTestParticipantsView.as_view(), name='register_test_participants'),
    # FIXME: refactor these into POSTs using the ExperimentActionForm
#    url(r'^experiment/(?P<pk>\d+)/deactivate$', deactivate, name='deactivate'),
#    url(r'^experiment/(?P<pk>\d+)/clone$', CloneExperimentView.as_view(), name='clone'),
#    url(r'^experiment/(?P<pk>\d+)/clear-participants', ClearParticipantsExperimentView.as_view(), name='clear_participants'),
#    url(r'^experiment/(?P<pk>\d+)/add-participants/(?P<count>[\d]+)$', 'add_participants', name='add_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', download_data, name='download_data'),
    url(r'^experiment/(?P<pk>\d+)/export/configuration(?P<file_extension>.[\w]+)$', export_configuration, name='export_configuration'),
    url(r'^configuration/(?P<pk>\d+)/edit', edit_experiment_configuration, name='edit_experiment_configuration'),
    url(r'^experimenter/bookmark-experiment-metadata$', toggle_bookmark_experiment_metadata, name='bookmark_experiment_metadata'),
    url(r'^api/configuration/clone', clone_experiment_configuration, name='clone_experiment_configuration'),
    url(r'^api/experiment/(?P<pk>\d+)/check-ready-participants$', check_ready_participants, name='check_ready_participants'),
    url(r'^api/experiment/archive', archive, name='archive'),
    url(r'^api/experiment/clone', clone_experiment, name='clone_experiment'),
    url(r'^api/experiment/create', create_experiment, name='create_experiment'),
    url(r'^api/experimenter/save-notes', save_experimenter_notes, name='save-experimenter-notes'),
    url(r'^api/experimenter/experiment-controller', experiment_controller, name='experiment-controller'),
    url(r'^api/experimenter/round-data', get_round_data, name='get-round-data'),
    # match arbitrary experiment URL prefix fragments for logging / login / logout / accessing the dashboard view model
    url(r'api/log/(?P<participant_group_id>\d+)$', api_logger, name='api-logger'),
    url(r'api/login', participant_api_login, name='participant_api_login'),
    url(r'api/logout', api_logout, name='api_logout'),
    url(r'api/dashboard', get_dashboard_view_model, name='dashboard_view_model'),
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


