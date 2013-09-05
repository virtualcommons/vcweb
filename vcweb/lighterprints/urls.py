from django.conf.urls.defaults import url, patterns

from vcweb.lighterprints.views import (post_chat_message, post_comment, perform_activity, participate,
        group_activity, like, group_score, CsvExportView, checkin,
        get_view_model, mobile_participate, mobile_login)

# handles all /lighterprints/* URL requests
urlpatterns = patterns('vcweb.lighterprints.views',
    url(r'^(?P<pk>\d+)/data$', CsvExportView.as_view(), name='export-data'),
    url(r'^(?P<experiment_id>\d+)/participate/?$', participate, name='participate'),
    url(r'^api/view-model/(?P<participant_group_id>\d+)?', get_view_model),
    url(r'^api/group-activity/(?P<participant_group_id>\d+)', group_activity),
    url(r'^api/do-activity$', perform_activity),
    url(r'^api/message', post_chat_message),
    url(r'^api/comment', post_comment),
    url(r'^api/like', like),
    url(r'^api/group-score/(?P<participant_group_id>\d+)', group_score),
    url(r'^api/checkin', checkin),
    # FIXME: hacky, replace mobile login with core api login instead
    url(r'^mobile/login?$', mobile_login, name='mobile_login'),
    url(r'^mobile/?$', mobile_participate, name='mobile_participate'),
)
