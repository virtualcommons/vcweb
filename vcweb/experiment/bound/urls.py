from django.conf.urls import url

from vcweb.experiment.bound.views import (
    participate, submit_harvest_decision, get_view_model)

urlpatterns = [
    url(r'^(?P<experiment_id>\d+)/participate$',
        participate, name='participate'),
    url(r'^(?P<experiment_id>\d+)/view-model$',
        get_view_model, name='view_model'),
    url(r'^(?P<experiment_id>\d+)/submit-harvest-decision$',
        submit_harvest_decision, name='submit_harvest_decision'),
]
