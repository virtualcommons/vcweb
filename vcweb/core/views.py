# Create your views here.
from django.http import HttpResponse
from django.template import Context, loader
from django.template.context import RequestContext

from django.contrib.auth.decorators import *
from django.conf import settings

from vcweb.core.emailauth import EmailBackend

@login_required
def experimenter_index(request):
    t = loader.get_template('experimenter-index.html')
    c = RequestContext(request, {
                                 
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

def participant_index(request):
    # FIXME: check if logged in
    t = loader.get_template('participant-index.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))

