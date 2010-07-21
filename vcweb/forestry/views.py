# Create your views here.
from django.http import HttpResponse, Http404
from django.template import Context, loader
from django.template.context import RequestContext

def index(request):
    template = loader.get_template('forestry-index.html')
    context = RequestContext(request)
    return HttpResponse(template.render(context))

def configure(request):
    return Http404()


def experimenter(request):
    return Http404()