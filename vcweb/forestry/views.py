# Create your views here.
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template import Context, loader
from django.template.context import RequestContext

def index(request):
    return render_to_response('forestry/index.html', RequestContext(request))

def configure(request):
    return Http404()


def experimenter(request):
    return Http404()
