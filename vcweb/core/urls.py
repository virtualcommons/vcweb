from django.conf.urls.defaults import patterns, url
from django.contrib.auth.decorators import login_required
from vcweb.core.views import Dashboard, LoginView, LogoutView, RegistrationView, MonitorExperimentView, ConfigureExperimentView, CloneExperimentView
'''
URLs defined by the core vcweb app.
'''
urlpatterns = patterns('vcweb.core.views',
    url(r'^dashboard/?$', login_required(Dashboard.as_view()), name='dashboard'),
    url(r'^accounts/login/$', LoginView.as_view(), name='login'),
    url(r'^accounts/logout/$', LogoutView.as_view(), name='logout'),
    url(r'^accounts/register/$', RegistrationView.as_view(), name='register'),
    url(r'^accounts/profile/$', 'account_profile', name='profile'),
    url(r'^participate/(?P<pk>\d+)/instructions', 'instructions', name='instructions'),
    url(r'^participate/(?P<namespace>\w+)/instructions', 'instructions', name='namespace_instructions'),
    url(r'^experiment/(?P<pk>\d+)/monitor$', MonitorExperimentView.as_view(), name='monitor_experiment'),
    url(r'^experiment/(?P<pk>\d+)/configure$', ConfigureExperimentView.as_view(), name='configure_experiment'),
    url(r'^experiment/(?P<pk>\d+)/clone$', CloneExperimentView.as_view(), name='clone'),
#    url(r'^experiment/(?P<pk>\d+)/add-participants/(?P<count>[\d]+)$', 'add_participants', name='add_participants'),
#    url(r'^experiment/(?P<pk>\d+)/clear-participants', 'clear_participants', name='clear_participants'),
    url(r'^experiment/(?P<pk>\d+)/download/(?P<file_type>[\w]+)$', 'download_data', name='download_data'),
# experiment controller actions are the most general, needs to be matched at the very end
    url(r'^experiment/(?P<pk>\d+)/(?P<experiment_action>[\w-]+)$', 'experiment_controller', name='experiment_controller'),
    )
# add ajax actions
urlpatterns += patterns('vcweb.core.ajax',
    url(r'^ajax/(?P<pk>\d+)/(<?P<experiment_action[\w-]+)$', 'experiment_controller'),
    )
