from django.conf.urls import url, patterns, include
from vcweb.subject_pool import views


# session_urls = patterns('',
#     url(r'^$', ViewSession.as_view(), name='session_detail'),
#     url(r'^Update$', EditSession.as_view(), name='session_update'),
#     url(r'^Delete$', DeleteSession.as_view(), name='session_delete'),
# )

urlpatterns = patterns('vcweb.subject_pool.views',
    url(r'^session$', 'sessionListView', name='session'),
    url(r'^session/update$', 'update_session', name='update_session'),
)

# urlpatterns = patterns('vcweb.subject_pool.views',
#     #url(r'^$', 'index', name='index'),
#     url(r'^sessions/$', '', name='index'),
#     #url(r'^experiment/?$', 'experimenter_index', name='experimenter_index'),
#     #url(r'^$', SessionList.as_view(), name='session_list'),
#     #url(r'^(?P<slug>[\w-]+).session/', include(session_urls)),
# )
