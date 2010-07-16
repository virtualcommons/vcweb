# Create your views here.
from django.http import HttpResponse
from django.template import Context, loader


def index(request):
    t = loader.get_template('index.html')
    c = Context({
        'main': "Welcome!",
        'username':"foo",
    })
    return HttpResponse(t.render(c))

def list(request):
    t = loader.get_template('base_experimenter.html')
    c = Context({
        'main': "List of experiments!",
        'username':"foo",
    })
    return HttpResponse(t.render(c))

def configure(request):
    t = loader.get_template('base_participant.html')
    c = Context({
        'main': "configuration of the experiment!",
        'username':"foo",
    })
    return HttpResponse(t.render(c))