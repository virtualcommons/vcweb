from django.conf.urls import url

from .views import (
    post_chat_message, post_comment, perform_activity, participate, like, get_view_model,
    mobile_participate, download_payment_data,
)

urlpatterns = [
    url(r'^(?P<experiment_id>\d+)/participate/$', participate, name='participate'),
    url(r'^(?P<pk>\d+)/download-payment-data/$', download_payment_data, name='download_payment_data'),
    # used only by the increasingly out-of-date mobile UI
    url(r'^api/view-model/(?P<participant_group_id>\d+)?', get_view_model),
    url(r'^api/perform-activity$', perform_activity, name='perform_activity'),
    url(r'^api/message', post_chat_message, name='post_chat'),
    url(r'^api/comment', post_comment, name='post_comment'),
    url(r'^api/like', like, name='like'),
    # FIXME: hacky, replace mobile login with core api login instead?
    # url(r'^mobile/login?$', mobile_login, name='mobile_login'),
    url(r'^mobile/?$', mobile_participate, name='mobile_participate'),
]
