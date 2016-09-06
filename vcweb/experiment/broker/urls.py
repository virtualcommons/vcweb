from django.conf.urls import url

from .views import (participate, submit_decision, get_view_model, submit_chat_preferences)


urlpatterns = [
    url(r'^(?P<experiment_id>\d+)?/participate/?$', participate, name='participate'),
    url(r'^(?P<experiment_id>\d+)/submit-decision$', submit_decision, name='submit_decision'),
    url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='get_view_model'),
    url(r'^(?P<experiment_id>\d+)/submit-chat-preferences$', submit_chat_preferences, name='submit_chat_preferences'),
]
