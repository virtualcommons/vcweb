from django.conf.urls.defaults import url, patterns
from vcweb.broker.views import (participate, finished_instructions, submit_decision, get_view_model)

urlpatterns = patterns('vcweb.broker.views',
        url(r'^(?P<experiment_id>\d+)?/participate/?$', participate, name='participate'),
        url(r'^(?P<experiment_id>\d+)/submit-harvest-decision$', submit_decision, name='submit_decision'),
        url(r'^(?P<experiment_id>\d+)/finished-instructions$', finished_instructions, name='finished_instructions'),
        url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='get_view_model'),
        )

