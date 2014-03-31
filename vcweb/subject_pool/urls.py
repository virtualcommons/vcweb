from django.conf.urls import url, patterns

from vcweb.subject_pool.views import (experiment_session_signup, submit_experiment_session_signup,
                                      cancel_experiment_session_signup,)

urlpatterns = patterns('vcweb.subject_pool.views',
    url(r'^session$', 'session_list_view', name='index'),
    url(r'^session/update$', 'update_session', name='update_session'),
    url(r'^session/events$', 'get_session_events', name='session_events'),
    url(r'^session/detail/event/(\d+)$', 'manage_participant_attendance', name='session_event_detail'),
    url(r'^session/invite$', 'send_invitations', name='send_invites'),
    url(r'^session/invite/count$', 'get_invitations_count', name='get_invitations_count'),
    url(r'^session/attendance$', 'manage_participant_attendance', name='participant_attendance'),
    url(r'^session/email-preview$', 'invite_email_preview', name='invite_email_preview'),
    url(r'^signup/$', experiment_session_signup, name='experiment_session_signup'),
    url(r'^signup/submit/$', submit_experiment_session_signup, name='submit_experiment_session_signup'),
    url(r'^signup/cancel/$', cancel_experiment_session_signup, name='cancel_experiment_session_signup'),
    # FIXME: duplicate alias, remove soon
    url(r'^/participant/session/$', experiment_session_signup, ),
    )
