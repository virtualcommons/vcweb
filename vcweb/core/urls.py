from django.conf.urls.defaults import *
'''
URLs defined by the core vcweb app.
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'accounts/login/$', 'login', name='login'),
    url(r'accounts/logout/$', 'logout', name='logout'),
    url(r'accounts/register/$', 'register', name='register'),
    url(r'accounts/profile/$', 'account_profile', name='profile'),
    url(r'experimenter/$', 'experimenter_index', name='experimenter-index'),
    url(r'participant/$', 'participant_index', name='participant-index'),
    url(r'(?P<experiment_id>\d+)/instructions', 'instructions', name='instructions'),
    url(r'(?P<namespace>\w+)/instructions', 'instructions', name='namespace-instructions'),
    url(r'experimenter/configure/(?P<experiment_id>\d+)$', 'configure', name='configure-experiment'),
)
