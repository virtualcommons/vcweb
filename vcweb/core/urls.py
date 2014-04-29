import logging
import re
import urllib

from django.conf import settings
from django.conf.urls import url, include
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

from vcweb.core.ajax import (get_round_data, save_experimenter_notes, create_experiment, clone_experiment, archive)
from vcweb.core.views import (
    dashboard, LoginView, LogoutView, monitor, RegisterEmailListView, RegisterTestParticipantsView, completed_survey,
    toggle_bookmark_experiment_metadata, check_survey_completed, Participate, download_data, download_participants,
    export_configuration, api_logger, participant_api_login, api_logout, participant_ready, check_ready_participants,
    get_dashboard_view_model, update_experiment, update_round_configuration, edit_experiment_configuration,
    clone_experiment_configuration, unsubscribe, update_round_param_value, update_experiment_param_value,
    update_experiment_configuration, OstromlabFaqList, cas_asu_registration, cas_asu_registration_submit,
    experiment_session_signup, submit_experiment_session_signup, cancel_experiment_session_signup,
    download_experiment_session, account_profile, update_account_profile, check_user_email, session_list_view,
    update_session, get_session_events, manage_participant_attendance, send_invitations, get_invitations_count,
    invite_email_preview, )


logger = logging.getLogger(__name__)

'''
URLs for the core vcweb app
'''
urlpatterns = [
    url(r'^cas/asu/$', cas_asu_registration, name='cas_asu_registration'),
    url(r'^cas/asu/submit/$', cas_asu_registration_submit, name='cas_asu_registration_submit'),
    url(r'^dashboard/$', dashboard, name='dashboard'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', login_required(LogoutView.as_view()), name='logout'),
    #url(r'^accounts/add/$', RegistrationView.as_view(), name='register'),
    url(r'^accounts/profile/$', account_profile, name='profile'),
    url(r'^accounts/profile/update$', update_account_profile, name='update_profile'),
    url(r'^accounts/check-email$', check_user_email, name='check_email'),
    url(r'^ostromlab/faq$', OstromlabFaqList.as_view(), name='ostromlab_faq'),
    url(r'^accounts/unsubscribe$', unsubscribe, name='unsubscribe'),
    url(r'^participate/?$', Participate.as_view(), name='participate'),
    url(r'^participate/survey-completed', completed_survey, name='survey_completed'),
    url(r'^participate/(?P<pk>\d+)/check-survey-completed', check_survey_completed, name='check_survey_completed'),
    url(r'^experiment/participant-ready$', participant_ready, name='participant_ready'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', monitor, name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/register-email-list$', RegisterEmailListView.as_view(), name='register_email_list'),
    url(r'^experiment/(?P<pk>\d+)/register-test-participants$',
        RegisterTestParticipantsView.as_view(), name='register_test_participants'),
    # FIXME: refactor these into POSTs using the ExperimentActionForm
    #    url(r'^experiment/(?P<pk>\d+)/deactivate$', deactivate, name='deactivate'),
    #    url(r'^experiment/(?P<pk>\d+)/clone$', CloneExperimentView.as_view(), name='clone'),
    #    url(r'^experiment/(?P<pk>\d+)/clear-participants', ClearParticipantsExperimentView.as_view(), name='clear_participants'),
    #    url(r'^experiment/(?P<pk>\d+)/add-participants/(?P<count>[\d]+)$', 'add_participants', name='add_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', download_data, name='download_data'),
    url(r'^experiment/(?P<pk>\d+)/download-participants/$', download_participants, name='download_participants'),
    url(r'^experiment/(?P<pk>\d+)/export/configuration(?P<file_extension>.[\w]+)$',
        export_configuration, name='export_configuration'),
    url(r'^configuration/(?P<pk>\d+)/edit', edit_experiment_configuration, name='edit_experiment_configuration'),
    url(r'^api/configuration/round/(?P<pk>\-?\d+)$', update_round_configuration, name='update_round_configuration'),
    url(r'^api/configuration/round/param/(?P<pk>\-?\d+)$', update_round_param_value, name='update_round_param_value'),
    url(r'^api/configuration/experiment/(?P<pk>\-?\d+)$', update_experiment_configuration,
        name='update_experiment_configuration'),
    url(r'^api/configuration/experiment/param/(?P<pk>\-?\d+)$', update_experiment_param_value,
        name='update_experiment_param_value'),
    url(r'^experimenter/bookmark-experiment-metadata$', toggle_bookmark_experiment_metadata,
        name='bookmark_experiment_metadata'),
    url(r'^api/configuration/clone', clone_experiment_configuration, name='clone_experiment_configuration'),
    url(r'^api/experiment/(?P<pk>\d+)/check-ready-participants$', check_ready_participants,
        name='check_ready_participants'),
    url(r'^api/experiment/archive', archive, name='archive'),
    url(r'^api/experiment/clone', clone_experiment, name='clone_experiment'),
    url(r'^api/experiment/create', create_experiment, name='create_experiment'),
    url(r'^api/experiment/update', update_experiment, name='update_experiment'),
    url(r'^api/experimenter/save-notes', save_experimenter_notes, name='save_experimenter_notes'),
    url(r'^api/experimenter/round-data', get_round_data, name='get_round_data'),
    # match arbitrary experiment URL prefix fragments for logging / login / logout / accessing the dashboard view model

    url(r'api/log/(?P<participant_group_id>\d+)$', api_logger, name='api_logger'),
    url(r'api/login', participant_api_login, name='participant_api_login'),
    url(r'api/logout', api_logout, name='api_logout'),
    url(r'api/dashboard', get_dashboard_view_model, name='dashboard_view_model'),
    url(r'bug-report', RedirectView.as_view(url='https://bitbucket.org/virtualcommons/vcweb/issues/new'), name='report_issues'),
    # subject pool urls
    url(r'^subject-pool/session$', session_list_view, name='subject_pool_index'),
    url(r'^subject-pool/session/update$', update_session, name='update_session'),
    url(r'^subject-pool/session/events$', get_session_events, name='session_events'),
    url(r'^subject-pool/session/detail/event/(\d+)$', manage_participant_attendance, name='session_event_detail'),
    url(r'^subject-pool/session/invite$', send_invitations, name='send_invites'),
    url(r'^subject-pool/session/invite/count$', get_invitations_count, name='get_invitations_count'),
    url(r'^subject-pool/session/attendance$', manage_participant_attendance, name='participant_attendance'),
    url(r'^subject-pool/session/email-preview$', invite_email_preview, name='invite_email_preview'),
    url(r'^subject-pool/signup/$', experiment_session_signup, name='experiment_session_signup'),
    url(r'^subject-pool/signup/submit/$', submit_experiment_session_signup, name='submit_experiment_session_signup'),
    url(r'^subject-pool/signup/cancel/$', cancel_experiment_session_signup, name='cancel_experiment_session_signup'),
    url(r'^subject-pool/session/(?P<pk>\d+)/download/$', download_experiment_session,
        name='download_experiment_session'),
]



def experiment_urls():
    # crude filter, if experiment is in the app_name, include it
    experiments = [app_name for app_name in settings.INSTALLED_APPS if 'experiment' in app_name]
    for experiment in experiments:
        experiment_name = experiment.rpartition('.')[2]
        yield url(r'^' + experiment_name + '/', include(experiment + '.urls', namespace=experiment_name, app_name=experiment_name))

urlpatterns += experiment_urls()



def foursquare_auth_dict(**kwargs):
    return dict(kwargs, client_id=settings.FOURSQUARE_CONSUMER_KEY, client_secret=settings.FOURSQUARE_CONSUMER_SECRET,
                v=settings.FOURSQUARE_CONSUMER_DATE_VERIFIED)


def foursquare_url(url, **kwargs):
    url = "%s?%s" % (url, urllib.urlencode(foursquare_auth_dict(**kwargs)))
    logger.debug("%s", url)
    return url


def foursquare_venue_search_url(**kwargs):
    return foursquare_url(settings.FOURSQUARE_VENUE_SEARCH_ENDPOINT, **kwargs)


def foursquare_categories_url(**kwargs):
    return foursquare_url(settings.FOURSQUARE_CATEGORIES_ENDPOINT, **kwargs)
