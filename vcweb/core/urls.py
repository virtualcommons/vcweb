from django.conf.urls.defaults import *
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'$', 'index', name='core-index'),
    url(r'list/$', 'experimenter_index', name='experimenter-index'),
    url(r'participate/$', 'participant_index', name='participant-index'),
    url(r'experimenter/configure/(?P<game_instance_id>\d+)$', 'configure', name='configure-experiment'),
)