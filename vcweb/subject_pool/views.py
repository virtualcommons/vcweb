from django.views.generic import View
from django.shortcuts import render, redirect, RequestContext
from vcweb.core.models import is_experimenter, Experiment, ExperimentSession, ExperimentMetadata
from django.http import HttpResponse
from vcweb.core.decorators import experimenter_required
import datetime
from django.views.generic.list import ListView, TemplateResponseMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse

import logging

logger = logging.getLogger(__name__)
# @experimenter_required
# def index(request):
#     return render_to_response('subject-pool/experimenter-index.html', locals(), context_instance=RequestContext(request))

def index(request):
    return HttpResponse("Hello world!")

@experimenter_required
def sessionListView(request):
    user = request.user
    data = ExperimentSession.objects.filter(creator = user)
    logger.debug(data)
    metadata = ExperimentMetadata.objects.all()
    session = {
      1: ["bound","20/8/2013","20/9/2013", "30/9/2013", "50" ],
      2: ["broker","19/8/2013","21/9/2013", "26/9/2013", "30" ],
      3: ["forestry","25/8/2013","25/9/2013", "30/9/2013", "50" ],
      4: ["lighterprints","20/8/2013","20/9/2013", "30/9/2013", "50" ]

    }
    return render(request,"subject-pool/experimenter-index.html",{"sessions": session, "experiment_metadata" : metadata})