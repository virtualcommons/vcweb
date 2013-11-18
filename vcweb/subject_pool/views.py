from django.contrib import messages
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
from django.shortcuts import render
from vcweb.core.models import ExperimentSession, ExperimentMetadata, Participant, ParticipantSignup, Invitation, Institution
from vcweb.core.decorators import experimenter_required
from datetime import datetime, time, timedelta
from time import mktime
from vcweb.core import dumps
from vcweb.core.http import JsonResponse
from django.core.mail import send_mass_mail

from forms import SessionForm, SessionInviteForm, ParticipantAttendanceForm

import random
import logging

logger = logging.getLogger(__name__)


@experimenter_required
def session_list_view(request):
    experimenter = request.user.experimenter
    data = ExperimentSession.objects.filter(creator=request.user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]
    #logger.debug(experiment_metadata_list)
    session_list = [{
        "pk": session.pk,
        "experiment_metadata": session.experiment_metadata,
        "startDate": session.scheduled_date.date(),
        "startHour": session.scheduled_date.time().hour,
        "startMin": session.scheduled_date.time().minute,
        "endDate": session.scheduled_end_date.date(),
        "endHour": session.scheduled_end_date.time().hour,
        "endMin": session.scheduled_end_date.time().minute,
        "capacity": session.capacity,
        "location": session.location,
        "invite_count": Invitation.objects.filter(experiment_session=session).count()
    }for session in data]

    session_data = {
        "session_list": session_list,
        "experiment_metadata_list": experiment_metadata_list
    }

    form = SessionInviteForm()

    return render(request, "subject-pool/experimenter-index.html", {"view_model_json": dumps(session_data), "form": form})

@experimenter_required
def update_session(request):
    user = request.user
    form = SessionForm(request.POST or None)
    if form.is_valid():
        pk = form.cleaned_data.get('pk')
        request_type = form.cleaned_data.get('request_type')
        if request_type == 'delete':
            es = ExperimentSession.objects.get(pk=pk)
            es.delete()
        else:
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
            es.location = form.cleaned_data.get('location')
            es.creator = user
            es.date_created = datetime.now()
            exp_pk = form.cleaned_data.get("experiment_metadata_pk")
            es.experiment_metadata = ExperimentMetadata.objects.get(pk=exp_pk)
            es.save()

        return JsonResponse(dumps({
            'success': True,
            'session': es
        }))
    return JsonResponse(dumps({
        'success': False,
        'message': form.errors
    }))


def get_session_events(request):

    from_date = request.GET.get('from', None)
    to_date = request.GET.get('to', None)

    queryset = ExperimentSession.objects.filter()

    if to_date:
        queryset = queryset.filter(
            scheduled_end_date__gte=timestamp_to_datetime(from_date)
        )

    objects_body = []
    for event in queryset:
        index = event.pk % 20  # for color selection
        field = {
            "id": event.pk,
            "title": event.experiment_metadata.title,
            "url": "session/detail/event/" + str(event.pk),
            "class": "event-color-" + str(index),
            "start": datetime_to_timestamp(event.scheduled_date),
            "end": datetime_to_timestamp(event.scheduled_end_date),
            "capacity": event.capacity
        }
        objects_body.append(field)

    objects_head = {"success": True, "result": objects_body}

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


@experimenter_required
def send_invitations(request):
    user = request.user
    form = SessionInviteForm(request.POST or None)
    message = "Please fill all details of the invitation form"
    if form.is_valid():
        invitation_subject = form.cleaned_data.get('invitation_subject')
        invitation_text = form.cleaned_data.get('invitation_text')
        # current logged in experimenter is the sender of the invitations.
        from_email = user.email

        session_pk_list = request.POST.get('session_pk_list').split(",")
        no_of_invitations = form.cleaned_data.get('no_of_people')
        affiliated_university = form.cleaned_data.get('affiliated_university')

        experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)

        # get the experiment metadata pk of any session, as all sessions selected by experimenter to send invitations
        # belong to same experiment metadata(This is ensured as it is a constraint)
        experiment_metadata_pk = experiment_sessions[0].experiment_metadata.pk

        potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_university)
        potential_participants_count = len(potential_participants)

        final_participants = None

        if potential_participants_count == 0:
            # logger.debug("You Have already sent out invitations to all potential participants")
            message = "You Have already sent out invitations to all potential participants"
        else:
            if potential_participants_count < no_of_invitations:
                final_participants = random.sample(potential_participants, potential_participants_count)
                # logger.debug("Invitations were sent to only %s participants", potential_participants_count)
                message = "Your invitations were sent to only " + str(potential_participants_count) + " participants"
            else:
                final_participants = random.sample(potential_participants, no_of_invitations)
                # logger.debug("Invitations were sent to %s participants", no_of_invitations)
                message = "Your invitations were sent to " + str(no_of_invitations) + " participants"

            today = datetime.now()
            invitations = []
            recipient_list = []
            for participant in final_participants:
                recipient_list.append(participant.email)
                for es in experiment_sessions:
                    invitations.append(Invitation(participant=participant, experiment_session=es, date_created=today,
                                                  sender=user))

            # logger.debug(len(recipient_list))

            datatuple = (invitation_subject, invitation_text, from_email, recipient_list)

            send_mass_mail((datatuple, ), fail_silently=False)

            Invitation.objects.bulk_create(invitations)

        return JsonResponse(dumps({
            'success': True,
            'message': message,
            'invitesCount': potential_participants_count
        }))
    else:
        # logger.debug("Form is not valid")
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def get_potential_participants(experiment_metadata_pk, institution="Arizona S U", days_threshold=7):
    # Get the institution object
    affiliated_institution = Institution.objects.get(name=institution)
    # Get unlikely participants for the given parameters
    unlikely_participants = get_unlikely_participants(days_threshold, experiment_metadata_pk)

    potential_participants = Participant.objects.filter(can_receive_invitations=True,
                                                        institution=affiliated_institution)\
        .exclude(pk__in=unlikely_participants)

    return potential_participants


def get_unlikely_participants(days_threshold, experiment_metadata_pk):
    last_week_date = datetime.now() - timedelta(days=days_threshold)
    # invited_in_last_threshold_days contains all Invitations that were generated in last threshold days for the
    # given Experiment metadata
    invited_in_last_threshold_days = Invitation.objects\
        .filter(date_created__gt=last_week_date, experiment_session__experiment_metadata__pk=experiment_metadata_pk)

    # filtered_list is the list of participants who have received invitations for the given
    # experiment_metadata in last threshold days
    filtered_list = [inv.participant.pk for inv in invited_in_last_threshold_days]

    signup_participants = ParticipantSignup.objects.registered(experiment_metadata_pk=experiment_metadata_pk)
    # filtered_list1 is the list of participants who has already participated in the
    # given Experiment Metadata(in the past or currently participating)
    filtered_list1 = [p.invitation.participant.pk for p in signup_participants]

    # returned list the list of participants who have already received invitations in last threshold days or have already
    # participated in same experiment
    return list(set(filtered_list) | set(filtered_list1))


@experimenter_required
def manage_participant_attendance(request, pk=None):
    AttendanceFormSet = modelformset_factory(ParticipantSignup, form=ParticipantAttendanceForm,
                                             exclude=('date_created',), extra=0)
    es = ExperimentSession.objects.get(pk=pk)
    invitations_sent = Invitation.objects.filter(experiment_session=es)
    session_detail = {'experiment_metadata': es.experiment_metadata, 'start_date': es.scheduled_date.date(),
                      'start_time': es.scheduled_date.strftime('%I:%M %p'), 'end_date': es.scheduled_end_date.date(),
                      'end_time': es.scheduled_end_date.strftime('%I:%M %p'), 'location': es.location,
                      'capacity': es.capacity}

    if request.method == "POST":
        formset = AttendanceFormSet(request.POST,
                                    queryset=ParticipantSignup.objects.select_related('invitation__participant')
                                    .filter(invitation__in=invitations_sent))
        if formset.is_valid():
            messages.add_message(request, messages.SUCCESS, 'Well done...Your changes were successfully saved.')
            if formset.has_changed():
                formset.save()
        else:
            messages.add_message(request, messages.ERROR,
                                 'Something went wrong...Your changes were not saved. Please try again')
    else:
        formset = AttendanceFormSet(queryset=ParticipantSignup.objects.filter(invitation__in=invitations_sent))

    return render(request, 'subject-pool/session_detail.html', {'session_detail': session_detail, 'formset': formset})