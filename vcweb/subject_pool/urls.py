from django.conf.urls import url, patterns

urlpatterns = patterns('vcweb.subject_pool.views',
    url(r'^session$', 'sessionListView', name='session'),
    url(r'^session/update$', 'update_session', name='update_session'),
    url(r'^session/events$', 'get_session_events', name='session_events'),
)

