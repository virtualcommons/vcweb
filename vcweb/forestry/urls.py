from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('vcweb.forestry.views',
    url(r'^$', 'index', name='index'),
    url(r'^participate/?$', 'participant_index', name='participant_index'),
    url(r'^experiment/?$', 'experimenter_index', name='experimenter_index'),
    url(r'^configure/(?P<experiment_id>\d+)$', 'configure', name='configure'),
    url(r'^(?P<experiment_id>\d+)/experimenter$', 'manage_experiment', name='manage_experiment'),
    url(r'^(?P<experiment_id>\d+)/wait$', 'wait', name='wait'),
    url(r'^(?P<experiment_id>\d+)/participate$', 'participate', name='participate'),
)
