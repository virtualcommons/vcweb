from django.conf.urls.defaults import *
'''
URLs defined by the core vcweb app.
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'dashboard/$', 'dashboard', name='dashboard'),
    url(r'accounts/login/$', 'login', name='login'),
    url(r'accounts/logout/$', 'logout', name='logout'),
    url(r'accounts/register/$', 'register', name='register'),
    url(r'accounts/profile/$', 'account_profile', name='profile'),
    url(r'experiment/$', 'experimenter_index', name='experimenter_index'),
    url(r'participate/$', 'participant_index', name='participant_index'),
    url(r'(?P<experiment_id>\d+)/instructions', 'instructions', name='instructions'),
    url(r'(?P<namespace>\w+)/instructions', 'instructions', name='namespace_instructions'),
    url(r'experiment/(?P<experiment_id>\d+)/monitor$', 'monitor', name='monitor_experiment'),
    url(r'experiment/(?P<experiment_id>\d+)/configure$', 'configure', name='configure_experiment'),
)
