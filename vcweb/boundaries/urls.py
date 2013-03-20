from django.conf.urls.defaults import url, patterns
from vcweb.boundaries.views import (participate, submit_harvest_decision, get_view_model)

urlpatterns = patterns('vcweb.boundaries.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^(?P<experiment_id>\d+)/experimenter$', 'monitor_experiment', name='monitor_experiment'),
    url(r'^(?P<experiment_id>\d+)/participate$', participate, name='participate'),
    url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='view_model'),
    url(r'^(?P<experiment_id>\d+)/submit-harvest-decision$', submit_harvest_decision, name='submit_harvest_decision'),
)
