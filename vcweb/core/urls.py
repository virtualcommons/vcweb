from django.conf.urls.defaults import *
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'$', 'index', name='core-index'),
    url(r'list/$', 'experimenter_list', name='list-experiments'),
    url(r'participate/$', 'participate', name='participate'),
    url(r'experimenter/configure/(?P<game_instance_id>\d+)$', 'configure', name='configure-experiment'),
)