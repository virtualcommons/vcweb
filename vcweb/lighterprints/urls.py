from django.conf.urls.defaults import url, patterns
from django.views.decorators.cache import never_cache

from vcweb.lighterprints.views import (ActivityDetailView, ActivityListView, MobileView,
        post_chat_message, post_comment, perform_activity, DiscussionBoardView, login,
        group_activity, like, get_notifications, update_notifications_since, group_points_summary)

# handles all /lighterprints/* URL requests
urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^mobile$', MobileView.as_view(), name='mobile'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^activity/list/?$', never_cache(ActivityListView.as_view())),
    url(r'^activity/(?P<activity_id>\d+)$', never_cache(ActivityDetailView.as_view())),
    url(r'^discussion/(?P<experiment_id>\d+)/(?P<participant_id>\d+)', DiscussionBoardView.as_view()),
    url(r'^api/group-activity/(?P<participant_group_id>\d+)', never_cache(group_activity)),
    url(r'^api/do-activity$', perform_activity),
    url(r'^api/message', post_chat_message),
    url(r'^api/comment', post_comment),
    url(r'^api/like', like),
    url(r'^api/login', login),
    url(r'^api/group-points-summary', group_points_summary),
    url(r'^api/summary/clear', update_notifications_since),
    url(r'^api/summary/(?P<participant_group_id>\d+)', get_notifications),
)
