from django.conf.urls import url, patterns

urlpatterns = patterns('vcweb.subject_pool.views',
    url(r'^session$', 'session_list_view', name='session'),
    url(r'^session/update$', 'update_session', name='update_session'),
    url(r'^session/events$', 'get_session_events', name='session_events'),
    url(r'^session/detail/event/(\d+)$', 'manage_participant_attendance', name='session_event_detail'),
    url(r'^session/invite$', 'send_invitations', name='send_invites'),
    url(r'^session/attendance$', 'manage_participant_attendance', name='participant_attendance')
)