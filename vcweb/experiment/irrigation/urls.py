from django.conf.urls import url

from .views import participate, get_view_model, control_gate

urlpatterns = [
    url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='view_model'),
    url(r'^(?P<experiment_id>\d+)/participate$', participate, name='participate'),
    url(r'^(?P<experiment_id>\d+)/control-gate$', control_gate, name='control_gate'),
]
