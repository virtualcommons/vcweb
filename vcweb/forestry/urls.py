from django.conf.urls.defaults import url, patterns
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.forestry.views',
    url(r'$', 'index', name='index'),
    url(r'experimenter/$', 'experimenter', name='experimenter'),
    url(r'configure/(?P<game_instance_id>\d+)$', 'configure', name='configure-experiment'),
)
