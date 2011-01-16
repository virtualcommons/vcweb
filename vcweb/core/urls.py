from django.conf.urls.defaults import *
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'accounts/login/$', 'login', name='login'),
    url(r'accounts/logout/$', 'logout', name='logout'),
    url(r'accounts/register/$', 'register', name='register'),
    url(r'accounts/profile/$', 'account_profile', name='profile'),
    url(r'experimenter/$', 'experimenter_index', name='experimenter-index'),
    url(r'participant/$', 'participant_index', name='participant-index'),
    url(r'(?P<experiment_id>\d+)|(?P<experiment_namespace>\w+)/instructions', 'instructions', name='instructions'),
    url(r'experimenter/configure/(?P<experiment_id>\d+)$', 'configure', name='configure-experiment'),
)
