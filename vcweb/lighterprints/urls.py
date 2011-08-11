from django.conf.urls.defaults import url, patterns

from vcweb.lighterprints.views import (ActivityDetailView, ActivityListView, MobileView,
        post_chat_message, perform_activity, DiscussionBoardView, login,
        group_activity)

urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^mobile$', MobileView.as_view(), name='mobile'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^activity/list/?$', ActivityListView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)$', ActivityDetailView.as_view()),
    url(r'^discussion/(?P<experiment_id>\d+)/(?P<participant_id>\d+)', DiscussionBoardView.as_view()),
    url(r'^api/group-activity/(?P<participant_group_id>\d+)', group_activity),
    url(r'^api/do-activity$', perform_activity),
    url(r'^api/post-chat', post_chat_message),
    url(r'^api/login', login),
)
