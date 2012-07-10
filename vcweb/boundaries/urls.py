from django.conf.urls.defaults import url, patterns
from django.views.generic import TemplateView

urlpatterns = patterns('vcweb.boundaries.views',
    url(r'^$', 'index', name='index'),
    url(r'^(?P<experiment_id>\d+)/configure$', 'configure', name='configure'),
    url(r'^(?P<experiment_id>\d+)/experimenter$', 'monitor_experiment', name='monitor_experiment'),
    url(r'^(?P<experiment_id>\d+)/participate$', 'participate', name='participate'),
    url(r'^(?P<experiment_id>\d+)/consent$', 'consent', name='consent'),
    url(r'^(?P<experiment_id>\d+)/survey$', 'survey', name='survey'),
    url(r'^(?P<experiment_id>\d+)/quiz$', 'quiz', name='quiz'),
    url(r'^tutorial$', TemplateView.as_view(template_name='boundaries/tutorial.html'), name='tutorial'),
    url(r'^(?P<experiment_id>\d+)/instructions$', 'instructions', name='instructions'),
)
