from django.conf.urls.defaults import url, patterns
from django.views.decorators.cache import cache_page

from vcweb.lighterprints.views import (ActivityDetailView, ActivityListView, MobileView, post_chat_message,
        post_comment, perform_activity, DiscussionBoardView, login, participate, group_activity, like,
        get_notifications, update_notifications_since, group_score, CsvExportView, checkin)

# handles all /lighterprints/* URL requests
urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^mobile$', MobileView.as_view(), name='mobile'),
    url(r'^(?P<pk>\d+)/data$', CsvExportView.as_view(), name='export-data'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^((?P<experiment_id>\d+)/)?participate/?$', participate, name='participate'),
    url(r'^activity/list(?P<format>.html|.json)?/?$', ActivityListView.as_view()),
    url(r'^activity/(?P<activity_id>\d+)$', cache_page(60*15)(ActivityDetailView.as_view())),
    url(r'^discussion/(?P<experiment_id>\d+)/(?P<participant_id>\d+)', DiscussionBoardView.as_view()),
    url(r'^api/group-activity/(?P<participant_group_id>\d+)', group_activity),
    url(r'^api/do-activity$', perform_activity),
    url(r'^api/message', post_chat_message),
    url(r'^api/comment', post_comment),
    url(r'^api/like', like),
    url(r'^api/login', login),
    url(r'^api/group-score/(?P<participant_group_id>\d+)', group_score),
    url(r'^api/notifications/clear', update_notifications_since),
    url(r'^api/notifications/(?P<participant_group_id>\d+)', get_notifications),
    url(r'^api/checkin', checkin),
)
