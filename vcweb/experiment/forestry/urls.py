from django.conf.urls import url, patterns

from vcweb.experiment.forestry.views import participate, get_view_model, submit_harvest_decision


urlpatterns = patterns('vcweb.experiment.forestry.views',
                       url(r'^(?P<experiment_id>\d+)/view-model$', get_view_model, name='view_model'),
                       url(r'^(?P<experiment_id>\d+)/participate$', participate, name='participate'),
                       url(r'^(?P<experiment_id>\d+)/submit-harvest-decision$', submit_harvest_decision,
                           name='submit_harvest_decision'),
)
