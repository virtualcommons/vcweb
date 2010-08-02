from django.conf.urls.defaults import *
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'accounts/login/$', 'login', name='login'),
    url(r'accounts/register/$', 'register', name='register'),
    url(r'accounts/profile/$', 'account_profile', name='profile'),
    url(r'list/$', 'experimenter_index', name='experimenter_index'),
    url(r'participate/$', 'participant_index', name='participant-index'),
    url(r'experimenter/configure/(?P<game_instance_id>\d+)$', 'configure', name='configure-experiment'),
)
