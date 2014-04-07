from django.conf.urls import url, patterns
from vcweb.forestry.views import participate


urlpatterns = patterns('vcweb.forestry.views',
    url(r'^(?P<experiment_id>\d+)/participate$', participate, name='participate'),
)
