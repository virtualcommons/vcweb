from django.views.generic import View
from django.shortcuts import render, redirect, RequestContext
from vcweb.core.models import is_experimenter, Experiment, ExperimentSession, ExperimentMetadata
from django.http import HttpResponse
from vcweb.core.decorators import experimenter_required
from datetime import datetime, time
from time import mktime
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
    session_list = [{"pk": session.pk, "experiment": session.experiment_metadata, "startDate": session.scheduled_date.date(), "startHour": session.scheduled_date.time().hour, "startMin": session.scheduled_date.time().minute, "endDate": session.scheduled_end_date.date(),"endHour": session.scheduled_end_date.time().hour, "endMin": session.scheduled_end_date.time().minute, "capacity": session.capacity} for session in data]
    session_data = {"sessions": session_list, "experiments": experiment_metadata_list}
    #logger.debug(session_data)
    return render(request,"subject-pool/experimenter-index.html",{"view_model_json": dumps(session_data)})

@experimenter_required
def update_session(request):
    user = request.user
    form = SessionForm(request.POST or None)
    if form.is_valid():
        pk = form.cleaned_data.get('pk')
        request_type = form.cleaned_data.get('request_type')
        if request_type != 'delete':
            if request_type == 'create':
                es = ExperimentSession()
            elif request_type == 'update':
                es = ExperimentSession.objects.get(pk=pk)

            start_date = datetime.strptime(form.cleaned_data.get('start_date'), "%Y-%m-%d")
            start_time = time(int(form.cleaned_data.get('start_hour')), int(form.cleaned_data.get('start_min')))
            es.scheduled_date = datetime.combine(start_date, start_time)
            end_date = datetime.strptime(form.cleaned_data.get('end_date'), "%Y-%m-%d")
            end_time = time(int(form.cleaned_data.get('end_hour')), int(form.cleaned_data.get('end_min')))
            es.scheduled_end_date = datetime.combine(end_date, end_time)
            es.capacity = form.cleaned_data.get('capacity')
            es.creator = user
            es.date_created = datetime.now()
            exp = form.cleaned_data.get("experiment_meta_data")
            es.experiment_metadata = ExperimentMetadata.objects.get(pk = exp)

            es.save()
        else:
            es = ExperimentSession.objects.get(pk=pk)
            es.delete()

        return JsonResponse(dumps({
            'success': True,
            'session': es
        }))

    return JsonResponse(dumps({
            'success': False
        }))


def get_session_events(request):
    from_date = request.GET.get('from', False)
    to_date = request.GET.get('to', False)\

    logger.debug("from date %s", from_date)
    logger.debug("to date %s", to_date)

    queryset = ExperimentSession.objects.filter()

    logger.debug(timestamp_to_datetime(from_date))
    logger.debug(timestamp_to_datetime(to_date))

    if from_date:
        queryset = queryset.filter(
            scheduled_date__gte=timestamp_to_datetime(from_date)
        )
    if to_date:
        queryset = queryset.filter(
            scheduled_end_date__lte=timestamp_to_datetime(to_date)
        )
    logger.debug(queryset)

    objects_body = []

    for event in queryset:
        field = {
            "id": event.pk,
            "title": event.experiment_metadata.title,
            "url": "#",
            "start": datetime_to_timestamp(event.scheduled_date),
            "end": datetime_to_timestamp(event.scheduled_end_date)
        }
        objects_body.append(field)

    objects_head = {"success": True}
    objects_head["result"] = objects_body
    return JsonResponse(dumps(objects_head))

def timestamp_to_datetime(timestamp):
    """
    Converts string timestamp to datetime
    with json fix
    """
    if isinstance(timestamp, (str, unicode)):

        if len(timestamp) == 13:
            timestamp = int(timestamp) / 1000

        return datetime.fromtimestamp(timestamp)
    else:
        return ""


def datetime_to_timestamp(date):
    """
    Converts datetime to timestamp
    with json fix
    """
    if isinstance(date, datetime):

        timestamp = mktime(date.timetuple())
        json_timestamp = int(timestamp) * 1000

        return '{0}'.format(json_timestamp)
    else:
        return ""