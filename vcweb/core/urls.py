from django.conf.urls.defaults import patterns, url

'''
URLs defined by the core vcweb app.
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'^dashboard/?$', 'dashboard', name='dashboard'),
    url(r'^accounts/login/$', 'login', name='login'),
    url(r'^accounts/logout/$', 'logout', name='logout'),
    url(r'^accounts/register/$', 'register', name='register'),
    url(r'^accounts/profile/$', 'account_profile', name='profile'),
    url(r'^experiment/$', 'experimenter_index', name='experimenter_index'),
    url(r'^participate/$', 'participant_index', name='participant_index'),
    url(r'^participate/(?P<experiment_id>\d+)/instructions', 'instructions', name='instructions'),
    url(r'^participate/(?P<namespace>\w+)/instructions', 'instructions', name='namespace_instructions'),
    url(r'^experiment/(?P<experiment_id>\d+)/monitor$', 'monitor', name='monitor_experiment'),
    url(r'^experiment/(?P<experiment_id>\d+)/configure$', 'configure', name='configure_experiment'),
# experiment controller actions
    url(r'^experiment/(?P<experiment_id>\d+)/(?P<experiment_action>[\w-]+)$', 'experiment_controller', name='experiment_controller'),
    )
# add ajax actions

urlpatterns += patterns('vcweb.core.ajax',
    url(r'^ajax/(?P<experiment_id>\d+)/(<?P<experiment_action[\w-]+)$', 'experiment_controller'),
    )

