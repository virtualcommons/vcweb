from django.conf.urls import url

from vcweb.core.subjectpool.views import (experimenter_index, manage_experiment_session, get_session_events,
                                          manage_participant_attendance,
                                          send_invitations, get_invitations_count, invite_email_preview,
                                          experiment_session_signup, submit_experiment_session_signup,
                                          cancel_experiment_session_signup,
                                          download_experiment_session)

urlpatterns = [
    url(r'^$', experimenter_index, name='experimenter_index'),
    url(r'^session/manage$', manage_experiment_session, name='manage_experiment_session'),
    url(r'^session/events$', get_session_events, name='session_events'),
    url(r'^session/detail/event/(?P<pk>\d+)$', manage_participant_attendance, name='session_event_detail'),
    url(r'^session/invite$', send_invitations, name='send_invites'),
    url(r'^session/invite/count$', get_invitations_count, name='get_invitations_count'),
    url(r'^session/attendance$', manage_participant_attendance, name='participant_attendance'),
    url(r'^session/email-preview$', invite_email_preview, name='invite_email_preview'),
    url(r'^signup/$', experiment_session_signup, name='experiment_session_signup'),
    url(r'^signup/submit/$', submit_experiment_session_signup, name='submit_experiment_session_signup'),
    url(r'^signup/cancel/$', cancel_experiment_session_signup, name='cancel_experiment_session_signup'),
    url(r'^session/(?P<pk>\d+)/download/$', download_experiment_session, name='download_experiment_session'),
]
