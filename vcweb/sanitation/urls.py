from django.conf.urls.defaults import url, patterns

urlpatterns = patterns('vcweb.sanitation.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^(?P<experiment_id>\d+)/experimenter$', 'monitor_experiment', name='monitor_experiment'),
    url(r'^(?P<experiment_id>\d+)/participate$', 'participate', name='participate'),
    url(r'^(?P<experiment_id>\d+)/consent$', 'consent', name='consent'),
    url(r'^(?P<experiment_id>\d+)/survey$', 'survey', name='survey'),
    url(r'^(?P<experiment_id>\d+)/quiz$', 'quiz', name='quiz'),
    url(r'^(?P<experiment_id>\d+)/play$', 'play', name='play'),
    url(r'^(?P<experiment_id>\d+)/instructions$', 'instructions', name='instructions'),
)
