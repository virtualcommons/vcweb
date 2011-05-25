# Create your views here.
from vcweb.core.models import Experiment
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext

def configure(request, experiment_id=None):
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('sanitation/configure.html', {
        'experiment': experiment,
        },
        context_instance=RequestContext(request))

