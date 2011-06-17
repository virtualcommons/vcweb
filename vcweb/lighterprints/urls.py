from django.conf.urls.defaults import url, patterns

from vcweb.lighterprints.views import ActivityDetailView, ActivityListView, DoActivityView

urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^activity/list/?$', ActivityListView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)$', ActivityDetailView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)/do$', DoActivityView.as_view()),
)
