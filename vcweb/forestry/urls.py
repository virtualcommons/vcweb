from django.conf.urls.defaults import url, patterns
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.forestry.views',
    url(r'$', 'index', name='forestry-index'),
    url(r'experimenter/$', 'experimenter', name='forestry-experimenter'),
    url(r'configure/(?P<game_instance_id>\d+)$', 'configure', name='configure-experiment'),
)