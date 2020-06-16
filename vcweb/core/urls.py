import logging

from django.conf.urls import url
from django.views.generic import RedirectView, TemplateView
from rest_framework import routers

from . import views
from .api import (get_round_data, save_experimenter_notes, create_experiment, clone_experiment, is_email_available,
                  handle_chat_message, check_ready_participants, participant_ready, )
from .views import (dashboard, LoginView, LogoutView, monitor, RegisterEmailListView, RegisterTestParticipantsView,
                    completed_survey, toggle_bookmark_experiment_metadata, check_survey_completed, ParticipateView,
                    download_data, download_participants, export_configuration, get_dashboard_view_model,
                    update_experiment, update_round_configuration, show_experiment_configuration,
                    edit_experiment_configuration, delete_experiment_configuration, clone_experiment_configuration,
                    unsubscribe, update_round_param_value, update_experiment_param_value,
                    update_experiment_configuration, OstromlabFaqList, cas_asu_registration,
                    cas_asu_registration_submit, account_profile, update_account_profile, update_participants,
                    audit_report)

logger = logging.getLogger(__name__)

'''
URLs for core vcweb app
'''
urlpatterns = [
    url(r'^cas/asu/$', cas_asu_registration, name='cas_asu_registration'),
    url(r'^cas/asu/submit/$', cas_asu_registration_submit, name='cas_asu_registration_submit'),
    url(r'^papers/$', TemplateView.as_view(template_name='papers.html')),
    url(r'^dashboard/$', dashboard, name='dashboard'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', LogoutView.as_view(), name='logout'),
    # url(r'^accounts/add/$', RegistrationView.as_view(), name='register'), # XXX: open registration currently disabled
    url(r'^accounts/profile/$', account_profile, name='profile'),
    url(r'^accounts/mars-signup/$', views.PortOfMarsSignupView.as_view(), name='mars_registration'),
    url(r'^accounts/profile/update$', update_account_profile, name='update_profile'),
    url(r'^accounts/check-email$', is_email_available, name='check_email'),
    url(r'^ostromlab/faq/$', OstromlabFaqList.as_view(), name='ostromlab_faq'),
    url(r'^accounts/unsubscribe$', unsubscribe, name='unsubscribe'),
    url(r'^admin/audit-report$', audit_report, name='audit_report'),
    url(r'^participate/?$', ParticipateView.as_view(), name='participate'),
    url(r'^participate/survey-completed', completed_survey, name='survey_completed'),
    url(r'^participate/(?P<pk>\d+)/check-survey-completed', check_survey_completed, name='check_survey_completed'),
    url(r'^experiment/(?P<pk>\d+)/update-participants$', update_participants, name='update_participant'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', monitor, name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/register-email-list$', RegisterEmailListView.as_view(), name='register_email_list'),
    url(r'^experiment/(?P<pk>\d+)/register-test-participants$', RegisterTestParticipantsView.as_view(),
        name='register_test_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', download_data, name='download_data'),
    url(r'^experiment/(?P<pk>\d+)/download-participants/$', download_participants, name='download_participants'),
    url(r'^experiment/(?P<pk>\d+)/export/configuration(?P<file_extension>.[\w]+)$', export_configuration,
        name='export_configuration'),
    url(r'^configuration/(?P<pk>\d+)/$', show_experiment_configuration, name='show_experiment_configuration'),
    url(r'^configuration/(?P<pk>\d+)/edit', edit_experiment_configuration, name='edit_experiment_configuration'),
    url(r'^api/configuration/(?P<pk>\d+)/delete', delete_experiment_configuration,
        name='delete_experiment_configuration'),
    url(r'^api/configuration/round/(?P<pk>\-?\d+)$', update_round_configuration, name='update_round_configuration'),
    url(r'^api/configuration/round/param/(?P<pk>\-?\d+)$', update_round_param_value, name='update_round_param_value'),
    url(r'^api/configuration/experiment/(?P<pk>\-?\d+)$', update_experiment_configuration,
        name='update_experiment_configuration'),
    url(r'^api/configuration/experiment/param/(?P<pk>\-?\d+)$', update_experiment_param_value,
        name='update_experiment_param_value'),
    url(r'^experimenter/bookmark-experiment-metadata$', toggle_bookmark_experiment_metadata,
        name='bookmark_experiment_metadata'),
    url(r'^api/configuration/clone', clone_experiment_configuration, name='clone_experiment_configuration'),
    url(r'^api/experiment/participant-ready$', participant_ready, name='participant_ready'),
    url(r'^api/experiment/(?P<pk>\d+)/check-ready-participants$', check_ready_participants,
        name='check_ready_participants'),
    url(r'^api/experiment/(?P<pk>\d+)/chat$', handle_chat_message, name='handle_chat_message'),
    url(r'^api/experiment/clone', clone_experiment, name='clone_experiment'),
    url(r'^api/experiment/create', create_experiment, name='create_experiment'),
    url(r'^api/experiment/update', update_experiment, name='update_experiment'),
    url(r'^api/experimenter/save-notes', save_experimenter_notes, name='save_experimenter_notes'),
    url(r'^api/experimenter/round-data', get_round_data, name='get_round_data'),
    url(r'^api/dashboard', get_dashboard_view_model, name='dashboard_view_model'),
    url(r'bug-report', RedirectView.as_view(url='https://github.com/virtualcommons/vcweb/issues/new'),
        name='report_issues'),
    url(r'^autocomplete/participant-institution/$', views.InstitutionAutocomplete.as_view(),
        name='institution-autocomplete'),
    url(r'^autocomplete/participant-major/$', views.ParticipantMajorAutocomplete.as_view(),
        name='major-autocomplete'),
    # url(r'bug-report', BugReportFormView.as_view(), name='report_issues'),
    # match arbitrary experiment URL prefix fragments for logging / login /
    # logout / accessing the dashboard view model
    # url(r'api/log/(?P<participant_group_id>\d+)$', api_logger, name='api_logger'),
    # url(r'api/login', participant_api_login, name='participant_api_login'),
    # url(r'api/logout', api_logout, name='api_logout'),
    url(r'^contact/$', views.AntiSpamContactFormView.as_view(), name='contact_form'),
]

router = routers.DefaultRouter(trailing_slash=False)
router.register(r'experiments', views.ManageExperimentViewSet, basename='experiment')
