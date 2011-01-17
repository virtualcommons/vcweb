from django.conf.urls.defaults import url, patterns
from django.views.generic.simple import direct_to_template
urlpatterns = patterns('vcweb.forestry.views',
    url(r'^$', 'index', name='index'),
    url(r'^participate$', direct_to_template, { 'template':'forestry/participant-index.html' }, name='participant_index'),
    url(r'^experiment$', direct_to_template, { 'template':'forestry/experimenter-index.html' }, name='experimenter_index'),
    url(r'configure/(?P<experiment_id>\d+)$', 'configure', name='configure'),
    url(r'experiment/(?P<experiment_id>\d+)$', 'experimenter', name='experimenter-index'),
    url(r'(?P<experiment_id>\d+)', 'participate', name='participate'),
)
