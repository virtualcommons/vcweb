from django.conf.urls import url

from .views import participate, get_view_model, submit_decision

urlpatterns = [
    url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='view_model'),
    url(r'^(?P<experiment_id>\d+)/participate$', participate, name='participate'),
    url(r'^(?P<experiment_id>\d+)/submit-decision$', submit_decision, name='submit_decision'),
]
