from django.conf.urls.defaults import url, patterns

from vcweb.lighterprints.views import ActivityDetailView, ActivityListView

urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^activity/list$', ActivityListView.as_view()),
    url(r'^activity/(?P<activity_name>\w+)$', ActivityDetailView.as_view()),
)
