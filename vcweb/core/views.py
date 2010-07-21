# Create your views here.
from django.http import HttpResponse
from django.template import Context, loader
from django.template.context import RequestContext

from django.conf import settings

def index(request):
    t = loader.get_template('index.html')
    c = RequestContext(request, {
        'main': "Welcome!",
        'username':"foo",
        'template_dirs' : settings.TEMPLATE_DIRS,
    })
    return HttpResponse(t.render(c))

def experimenter_list(request):
    t = loader.get_template('base_experimenter.html')
    c = RequestContext(request, {
        'main': "List of experiments!",
        'username':"foo",
    })
    return HttpResponse(t.render(c))

def configure(request, game_instance_id):
# lookup game instance id (or create a new one?)
    t = loader.get_template('base_participant.html')
    c = RequestContext(request, {
        'main': "configuration of the experiment!",
        'username':"foo",
        
    })
    return HttpResponse(t.render(c))

def participate(request):
    # FIXME: check if logged in
    t = loader.get_template('participant_login.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))
