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
from vcweb.core import dumps
from vcweb.core.http import JsonResponse

import logging

logger = logging.getLogger(__name__)

@experimenter_required
def sessionListView(request):
    user = request.user
    data = ExperimentSession.objects.filter(creator=user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.all()]
    session_list = [{"pk": session.pk, "experiment": session.experiment_metadata, "startDate": session.scheduled_date, "endDate": session.scheduled_end_date} for session in data]
    session_data = {"sessions": session_list, "experiments": experiment_metadata_list}
    logger.debug(session_data)
    return render(request,"subject-pool/experimenter-index.html",{"view_model_json": dumps(session_data)})


def update_session(request):
    user = request.user
    session = request.POST
    logger.debug(session)
    if session["pk"] == -1:
        es = ExperimentSession()
    else:
        es = ExperimentSession.objects.get(pk=session.pk)

    es.scheduled_date = session.startDate
    es.scheduled_end_date = session.endDate
    es.capacity = session.capacity
    es.creator = user
    es.date_created = datetime.datetime().now()
    es.experiment_metadata = ExperimentMetadata.objects.get(title=session.experiment.title)

    es.save()

    return JsonResponse(dumps({
            'success': True,
            'session': es
        }))