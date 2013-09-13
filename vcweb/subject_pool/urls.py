from django.conf.urls import url, patterns, include
from views import SessionList, ViewSession, NewSession, DeleteSession,EditSession

session_urls = patterns('',
    url(r'^$', ViewSession.as_view(), name='session_detail'),
    url(r'^Update$', EditSession.as_view(), name='session_update'),
    url(r'^Delete$', DeleteSession.as_view(), name='session_delete'),
)

urlpatterns = patterns('vcweb.subject_pool.views',
    #url(r'^$', 'index', name='index'),
    url(r'^experiment/?$', 'experimenter_index', name='experimenter_index'),
    url(r'^$', SessionList.as_view(), name='session_list'),
    url(r'^(?P<slug>[\w-]+).session/', include(session_urls)),
)


