from django.conf.urls.defaults import url, patterns

from vcweb.lighterprints.views import (ActivityDetailView, ActivityListView, DoActivityView, MobileView,
        post_chat_message, DiscussionBoardView)

urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^mobile$', MobileView.as_view(), name='mobile'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^activity/list/?$', ActivityListView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)$', ActivityDetailView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)/do$', DoActivityView.as_view()),
    url(r'^discussion/(?P<experiment_id>\d+)/(?P<participant_id>\d+)', DiscussionBoardView.as_view()),
    url(r'^discussion/(?P<experiment_id>\d+)/post', post_chat_message),
)
