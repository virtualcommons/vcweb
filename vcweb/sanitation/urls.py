from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('vcweb.sanitation.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^(?P<experiment_id>\d+)/experimenter$', 'monitor_experiment', name='monitor_experiment'),
    url(r'^(?P<experiment_id>\d+)/participate$', 'participate', name='participate'),
)
