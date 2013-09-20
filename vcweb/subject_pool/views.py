from django.views.generic import View
from django.shortcuts import render, redirect, RequestContext
from vcweb.core.models import is_experimenter, Experiment, ExperimentSession, ExperimentMetadata
from django.http import HttpResponse
from vcweb.core.decorators import experimenter_required
import datetime
from django.views.generic import ListView, FormView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse
from vcweb.core import dumps
from vcweb.core.http import JsonResponse

from forms import SessionForm

import logging

logger = logging.getLogger(__name__)


@experimenter_required
def sessionListView(request):
    user = request.user
    data = ExperimentSession.objects.filter(creator=user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.all()]
    session_list = [{"pk": session.pk, "experiment": session.experiment_metadata, "startDate": str(session.scheduled_date), "endDate": str(session.scheduled_end_date), "capacity": session.capacity} for session in data]
    session_data = {"sessions": session_list, "experiments": experiment_metadata_list}
    #logger.debug(session_data)
    return render(request,"subject-pool/experimenter-index.html",{"view_model_json": dumps(session_data)})


def update_session(request):
    user = request.user
    form = SessionForm(request.POST or None)
    logger.debug("Outside form isValid function")
    if form.is_valid():
        logger.debug("I'm inside")
        pk = form.cleaned_data.get('pk')
        request_type = form.cleaned_data.get('request_type')
        logger.debug(request_type)
        if request_type != 'delete':
            if request_type == 'create':
                es = ExperimentSession()
            elif request_type == 'update':
                es = ExperimentSession.objects.get(pk=pk)

            es.scheduled_date = datetime.datetime.strptime(form.cleaned_data.get('start_date'), "%Y-%m-%d %H:%M")
            es.scheduled_end_date = datetime.datetime.strptime(form.cleaned_data.get('end_date'), "%Y-%m-%d %H:%M")
            es.capacity = form.cleaned_data.get('capacity')
            es.creator = user
            es.date_created = datetime.datetime.now()
            exp = form.cleaned_data.get("experiment_meta_data")
            es.experiment_metadata = ExperimentMetadata.objects.get(pk = exp)

            es.save()
        else:
            logger.debug("I'm here")
            es = ExperimentSession.objects.get(pk=pk)
            es.delete()

        return JsonResponse(dumps({
            'success': True,
            'session': es
        }))