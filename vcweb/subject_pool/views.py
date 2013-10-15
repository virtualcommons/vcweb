from django.shortcuts import render
from vcweb.core.models import ExperimentSession, ExperimentMetadata, Participant, ParticipantSignup, Invitation, Institution
from vcweb.core.decorators import experimenter_required
from datetime import datetime, time, timedelta
from time import mktime
from vcweb.core import dumps
from vcweb.core.http import JsonResponse

from forms import SessionForm, SessionDetailForm, SessionInviteForm

import random
import logging

logger = logging.getLogger(__name__)


@experimenter_required
def sessionListView(request):
    experimenter = request.user.experimenter
    data = ExperimentSession.objects.filter(creator=request.user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]
    logger.debug(experiment_metadata_list)
    session_list = [{"pk": session.pk, "experiment_metadata": session.experiment_metadata, "startDate": session.scheduled_date.date(), "startHour": session.scheduled_date.time().hour, "startMin": session.scheduled_date.time().minute, "endDate": session.scheduled_end_date.date(),"endHour": session.scheduled_end_date.time().hour, "endMin": session.scheduled_end_date.time().minute, "capacity": session.capacity} for session in data]
    session_data = {"session_list": session_list, "experiment_metadata_list": experiment_metadata_list}
    return render(request, "subject-pool/experimenter-index.html", {"view_model_json": dumps(session_data)})

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
            exp_pk = form.cleaned_data.get("experiment_metadata_pk")
            es.experiment_metadata = ExperimentMetadata.objects.get(pk=exp_pk)

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


    if to_date:
        queryset = queryset.filter(
            scheduled_end_date__gte=timestamp_to_datetime(from_date)
        )
    logger.debug(queryset)

    objects_body = []
    for event in queryset:
        index = event.pk % 20
        field = {
            "id": event.pk,
            "title": event.experiment_metadata.title,
            "url": "session/detail/event/" + str(event.pk),
            "class" : "event-color-" + str(index),
            "start": datetime_to_timestamp(event.scheduled_date),
            "end": datetime_to_timestamp(event.scheduled_end_date),
            "capacity": event.capacity
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


def get_session_event_detail(request, pk):
    es = ExperimentSession.objects.get(pk=pk)
    form = SessionDetailForm(instance=es)

    return render(request, 'subject-pool/session_detail.html', { 'form': form })

def send_invitations(request):
    user = request.user
    form = SessionInviteForm(request.POST or None)
    message = "Please provide all details in the invitation form"
    if form.is_valid():
        session_pk_list = form.cleaned_data.get('session_pk_list').split(",")
        no_of_invitations = form.cleaned_data.get('no_of_people')

        days_threshold = 7
        institution = "ASU"

        experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
        experiment_metadata_pk = experiment_sessions[0].experiment_metadata.pk

        potential_participants = get_potential_participants(institution, days_threshold, experiment_metadata_pk)
        potential_participants_count = len(potential_participants)

        if potential_participants_count == 0:
            logger.debug("You Have already sent out invitations to all potential participants")
            message = "You Have already sent out invitations to all potential participants"
        elif potential_participants_count < no_of_invitations:
            random.sample(get_potential_participants(institution, days_threshold, experiment_metadata_pk), potential_participants_count)
            logger.debug("Invitations were sent to only %s participants", potential_participants_count)
            message = "Invitations were sent to only " + str(potential_participants_count) + " participants"
        else:
            random.sample(get_potential_participants(institution, days_threshold, experiment_metadata_pk), no_of_invitations)
            logger.debug("Invitations were sent to %s participants", no_of_invitations)
            message = "Invitations were sent to " + str(no_of_invitations) + " participants"

        return JsonResponse(dumps({
            'success': True,
            'message': message
        }))
    else:
        logger.debug("Form is not valid")
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def get_potential_participants(institution, days_threshold, experiment_metadata_pk):
    affiliated_institution = Institution.objects.get(name=institution)
    unlikely_participants = get_unlikely_participants(days_threshold, experiment_metadata_pk)
    potential_participants = Participant.objects.filter(can_receive_invitations=True, institution=affiliated_institution).exclude(pk__in=unlikely_participants)

    return potential_participants


def get_unlikely_participants(days_threshold, experiment_metadata_pk):
    last_week_date = datetime.now() - timedelta(days=days_threshold)
    invited_and_signup_in_threshold_days = Invitation.objects.exclude(date_created__lt=last_week_date)
    # filtered_list is the list of participants who signed up for given experiment metadata is threshold days
    filtered_list = [inv.participant.pk for inv in invited_and_signup_in_threshold_days if inv.experiment_session.experiment_metadata.pk == experiment_metadata_pk]

    signup_participants = ParticipantSignup.objects.filter(attendance=0)
    filtered_list1 = [p.participant.pk for p in signup_participants if p.invitation.experiment_session.experiment_metadata_pk == experiment_metadata_pk]

    return list(set(filtered_list) | set(filtered_list1))