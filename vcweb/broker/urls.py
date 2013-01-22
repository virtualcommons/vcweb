from django.conf.urls.defaults import url, patterns
from vcweb.broker.views import participate

urlpatterns = patterns('vcweb.broker.views',
        url(r'^(?P<experiment_id>\d+)?/?participate/?$', participate, name='participate'),
        )

