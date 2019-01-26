from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.forms.models import modelformset_factory
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from vcweb.core.decorators import group_required, ownership_required
from vcweb.core.http import JsonResponse, dumps
from vcweb.core.models import (Participant, ParticipantSignup, PermissionGroup, ExperimentSession, ExperimentMetadata,
                               Invitation, send_markdown_email)
from vcweb.core.views import mimetypes

from .forms import (SessionInviteForm, ExperimentSessionForm, ParticipantAttendanceForm, CancelSignupForm)
from .models import InvitationEmail, generate_participant_report

from datetime import datetime
from time import mktime

import logging
import random
import unicodecsv
import markdown

logger = logging.getLogger(__name__)


@group_required(PermissionGroup.experimenter)
@require_GET
def subjectpool_index(request):
    """
    Provides subject recruitment interface with all the active and past experiment sessions.
    """
    experimenter = request.user.experimenter
    es_list = ExperimentSession.objects.select_related('experiment_metadata').filter(creator=request.user)
    session_list = [session.to_dict() for session in es_list]
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]
    potential_participants_count = Participant.objects.active().count()
    data = {
        'session_list': session_list,
        'experiment_metadata_list': experiment_metadata_list,
        'allEligibleParticipants': potential_participants_count,
        'potentialParticipantsCount': potential_participants_count,
    }
    return render(request, "subjectpool/index.html",
                  {"view_model_json": dumps(data), "form": SessionInviteForm()})


@group_required(PermissionGroup.experimenter)
@require_POST
@transaction.atomic
def manage_experiment_session(request, pk):
    form = ExperimentSessionForm(request.POST or None, pk=pk, user=request.user)
    if form.is_valid():
        es = form.save()
        return JsonResponse({'success': True, 'session': es})
    return JsonResponse({'success': False, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@require_GET
def get_session_events(request):
    """
    Returns the list of Experiment sessions that fall within the given range,
    Used by the subject pool calendar to display experiment sessions falling within the date range shown
    """
    from_date = request.GET.get('from', None)
    to_date = request.GET.get('to', None)
    criteria = dict()
    if to_date:
        criteria.update(scheduled_end_date__gte=timestamp_to_datetime(from_date))

    queryset = ExperimentSession.objects.select_related('experiment_metadata').filter(**criteria)
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

    return JsonResponse(objects_head)


def timestamp_to_datetime(timestamp):
    """
    Converts string timestamp to python datetime object with json fix
    """
    if isinstance(timestamp, str):

        if len(timestamp) == 13:
            timestamp = int(timestamp) / 1000

        return datetime.fromtimestamp(timestamp)
    else:
        return ""


def datetime_to_timestamp(date):
    """
    Converts python datetime object to timestamp with json fix
    """
    if isinstance(date, datetime):

        timestamp = mktime(date.timetuple())
        json_timestamp = int(timestamp) * 1000

        return '{0}'.format(json_timestamp)
    else:
        return ""


@group_required(PermissionGroup.experimenter)
@require_POST
def get_invitations_count(request):
    """
    API endpoint that returns the potential participant count based on the selected experiment metadata and Institution
    """
    form = SessionInviteForm(request.POST or None)
    if form.is_valid():
        session_pk_list = request.POST.get('session_pk_list').split(",")
        experiment_metadata_ids = ExperimentSession.objects.filter(pk__in=session_pk_list).values_list(
            'experiment_metadata__pk', flat=True)
        if len(set(experiment_metadata_ids)) == 1:
            # only allow invitations for sessions of a single ExperimentMetadata type
            # get the experiment metadata pk of any session (This is ensured as it is a constraint)
            potential_participants = Participant.objects.invitation_eligible(
                experiment_metadata_ids[0],
                gender=form.cleaned_data.get('gender'),
                institution=form.cleaned_data.get('affiliated_institution'),
                port_of_mars=form.cleaned_data.get('port_of_mars'),
                only_undergrad=form.cleaned_data.get('only_undergrad'))
            return JsonResponse({'success': True, 'invitesCount': len(potential_participants)})
    return JsonResponse({'success': False, 'invitesCount': 0, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@require_POST
def send_invitations(request):
    """
    Sends out invitation emails to random participants which match the required invitation criteria,
    using the provided email subject and message. Also returns the total number of invites sent.
    """
    user = request.user
    form = SessionInviteForm(request.POST or None)

    if form.is_valid():
        invitation_subject = form.cleaned_data.get('invitation_subject')
        invitation_text = form.cleaned_data.get('invitation_text')
        # use currently logged in experimenter as the sender of the
        # invitations.
        from_email = user.email

        session_pk_list = request.POST.get('session_pk_list').split(",")
        invitation_count = form.cleaned_data.get('number_of_people')
        affiliated_institution = form.cleaned_data.get('affiliated_institution')

        experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
        experiment_metadata_pk_list = experiment_sessions.values_list('experiment_metadata__pk', flat=True)

        if len(set(experiment_metadata_pk_list)) == 1:
            # get the experiment metadata pk of any session, as all sessions selected by experimenter to send
            # invitations belong to same experiment metadata (This has to be ensured as it is a constraint)
            experiment_metadata_pk = experiment_metadata_pk_list[0]

            potential_participants = list(Participant.objects.invitation_eligible(
                experiment_metadata_pk,
                institution=affiliated_institution,
                only_undergrad=form.cleaned_data.get('only_undergrad'),
                gender=form.cleaned_data.get('gender')))
            potential_participants_count = len(potential_participants)

            final_participants = None

            if potential_participants_count == 0:
                final_participants = []
                message = "There are no more eligible participants that can be invited for this experiment."
            else:
                if potential_participants_count < invitation_count:
                    # less candidate participants than the number of requested
                    # participants, use them all
                    final_participants = potential_participants
                else:
                    final_participants = random.sample(potential_participants, invitation_count)
                message = "Invitations were sent to %s / %s participants." % (len(final_participants), invitation_count)

                today = timezone.now()
                invitations = []
                recipient_list = [settings.DEFAULT_FROM_EMAIL]
                for participant in final_participants:
                    recipient_list.append(participant.email)
                    invitations.extend([Invitation(participant=participant,
                                                   experiment_session=es,
                                                   date_created=today,
                                                   sender=user)
                                        for es in experiment_sessions])
                Invitation.objects.bulk_create(invitations)

                if settings.ENVIRONMENT.is_production:
                    ie = InvitationEmail(request)
                    plaintext_content = ie.get_plaintext_content(invitation_text, session_pk_list)
                    html_content = markdown.markdown(plaintext_content)
                    msg = EmailMultiAlternatives(subject=invitation_subject, body=plaintext_content,
                                                 from_email=from_email, to=[from_email], bcc=recipient_list)
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                else:
                    logger.debug("Sending invitation emails in non-production environment is disabled: %s",
                                 recipient_list)
            return JsonResponse({'success': True, 'message': message, 'invitesCount': len(final_participants)})
        else:
            return JsonResponse({
                'success': False,
                'message': "Please select experiment sessions from the same experiment to send invitations."
            })
    # Form is not valid
    return JsonResponse({'success': False, 'errors': form.errors})


@group_required(PermissionGroup.experimenter)
@require_POST
def invite_email_preview(request):
    """
    Generates preview email for the provided invitation details
    """
    form = SessionInviteForm(request.POST or None)
    message = "Please fill in all the form fields to preview the invitation email."
    if form.is_valid():
        session_ids = request.POST.get('session_pk_list').split(",")
        invitation_text = form.cleaned_data.get('invitation_text')
        plaintext_content = InvitationEmail(request).get_plaintext_content(invitation_text, session_ids)
        html_content = markdown.markdown(plaintext_content)
        return JsonResponse({'success': True, 'content': html_content})
    return JsonResponse({'success': False, 'message': message})


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentSession)
def manage_participant_attendance(request, pk=None):
    """
    Performs Update or Get operation on the ParticipantSignup model depending upon the request.
    If request is GET, then the function will return the attendance formset. If request is POST then
    the function will update the Participant Attendance and return the updated formset.
    """
    es = get_object_or_404(ExperimentSession.objects, pk=pk)
    invitations_sent = Invitation.objects.filter(experiment_session=es)
    attendanceformset = modelformset_factory(ParticipantSignup, form=ParticipantAttendanceForm,
                                             exclude=('date_created',), extra=0)

    if request.method == "POST":
        formset = attendanceformset(request.POST, queryset=ParticipantSignup.objects.select_related(
            'invitation__participant__user').filter(invitation__in=invitations_sent))
        if formset.is_valid():
            messages.success(request, 'Your changes were successfully saved.')
            if formset.has_changed():
                formset.save()
        else:
            logger.debug("The formset was invalid with errors %s", formset.errors)
            messages.error(request, _("Invalid data. Please Try again."))
    else:
        formset = attendanceformset(queryset=ParticipantSignup.objects.select_related(
            'invitation__participant__user').filter(invitation__in=invitations_sent))

    return render(request, 'subjectpool/experiment-session-detail.html', {'session': es, 'formset': formset})


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentSession)
@require_POST
def add_participant(request, pk=None):
    participant_email = request.POST.get('participantEmail')
    participant = get_object_or_404(Participant.objects.select_related('user'), user__email=participant_email)
    es = get_object_or_404(ExperimentSession, pk=pk)
    # First check that the experiment session has already been completed
    if es.scheduled_end_date > timezone.now():
        logger.debug("%s tried to add participant %s to pending experiment session %s - ignoring",
                     request.user, participant, pk)
        return JsonResponse({'success': False, 'error': "You can't manually add a participant to a pending experiment session."})

    # there should only be a single invitation for a given experiment session and a given participant
    try:
        invitation = es.invitation_set.get(participant=participant)
    except Invitation.DoesNotExist:
        logger.debug("%s tried to add participant %s without an invitation to experiment session %s. Creating a new one.",
                     request.user, participant, pk)
        # create an invitation for that user
        invitation = Invitation.objects.create(participant=participant, experiment_session=es, sender=request.user)
    except Invitation.MultipleObjectsReturned:
        logger.error("Experiment session %s had multiple invitations created for participant %s", es, participant)
        invitation = es.invitation_set.first()

    # third and final check, the participant must not have already signed up for the experiment session
    if invitation.signup_set.exists():
        logger.debug("%s tried to add participant %s to experiment session %s but they are already signed up",
                     request.user, participant, pk)
        return JsonResponse({'success': False, 'error': 'Participant is already signed up for this experiment session'})
    else:
        ParticipantSignup.objects.create(invitation=invitation, attendance=ParticipantSignup.ATTENDANCE.participated)
        return JsonResponse({'success': True})


@group_required(PermissionGroup.participant)
@require_POST
def cancel_experiment_session_signup(request):
    form = CancelSignupForm(request.POST or None)
    if form.is_valid():
        signup = form.signup
        invitation = signup.invitation
        es = invitation.experiment_session
        if request.user.participant == invitation.participant:
            signup.delete()
            messages.success(request, _("You are no longer signed up for %s - thanks for letting us know!" % es))
        else:
            logger.error(
                "Invalid request: Participant %s tried to cancel signup %s", request.user.participant, signup)
            messages.error(request, _("You don't appear to be signed up for this session."))
    else:
        messages.error(request, _("Sorry, we couldn't process your request"))
    return redirect('core:dashboard')


@group_required(PermissionGroup.participant)
@require_POST
def submit_experiment_session_signup(request):
    """
    Enrolls the currently logged in user in the selected experiment session.
    """
    user = request.user
    invitation_pk = request.POST.get('invitation_pk')
    experiment_metadata_pk = request.POST.get('experiment_metadata_pk')
    invitation = get_object_or_404(Invitation.objects.select_related('experiment_session'), pk=invitation_pk)
    attendance = ParticipantSignup.ATTENDANCE.registered
    registered = waitlist = False
    message = ""

    # lock on the experiment session to prevent concurrent participant signups for an experiment session
    # exceeding its capacity
    with transaction.atomic():
        participant_signups = ParticipantSignup.objects.select_for_update().registered(
            experiment_session_pk=invitation.experiment_session_id)
        signup_count = participant_signups.count()

        experiment_session = invitation.experiment_session
        # verify for the vacancy in the selected experiment session before creating or updating participant signup entry
        if signup_count < experiment_session.capacity:
            registered = True
            message = '''You are now registered for this experiment session. A confirmation email has been sent and you
            should also receive a reminder email one day before the session. Thanks in advance for participating!'''
        elif experiment_session.waitlist:
            # signups are full, check if waitlists are full
            wc = ParticipantSignup.objects.waitlist(experiment_session_pk=invitation.experiment_session_id).count()
            if wc < experiment_session.waitlist_capacity:
                waitlist = True
                attendance = ParticipantSignup.ATTENDANCE.waitlist
                message = """This experiment session is currently full, but you have been added to the waitlist. You may
                still be able to participate in this experiment if other participants leave the experiment."""

    if registered or waitlist:
        # Check for any already registered or waitlisted participant signups for the current user
        ps = ParticipantSignup.objects.registered_or_waitlisted(invitation__participant=user.participant,
                                                                experiment_metadata_pk=experiment_metadata_pk)

        ps = ps.first() if ps.exists() else ParticipantSignup()

        ps.invitation = invitation
        ps.attendance = attendance
        ps.save()

        messages.success(request, _(message))
        send_markdown_email(template="subjectpool/email/confirmation-email.txt",
                            context={'session': invitation.experiment_session},
                            subject="Confirmation Email",
                            to_email=[user.email])
        return redirect('core:dashboard')
    else:
        messages.error(request, _("""This session is currently full. Please select a different session or try again
        later to see if any slots have opened up. Thank you for your interest!"""))
        return redirect('subjectpool:experiment_session_signup')


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentSession)
@require_GET
def download_experiment_session(request, pk=None):
    experiment_session = get_object_or_404(ExperimentSession.objects.select_related('creator'), pk=pk)

    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename=participants.csv'
    writer = unicodecsv.writer(response, encoding='utf-8')
    writer.writerow(["Participant list", experiment_session, experiment_session.location, experiment_session.capacity,
                     experiment_session.creator])
    writer.writerow(['Email', 'Name', 'Username', 'Class Status', 'Attendance'])
    for ps in ParticipantSignup.objects.select_related('invitation__participant').filter(invitation__experiment_session=experiment_session):
        participant = ps.invitation.participant
        writer.writerow([participant.email, participant.full_name, participant.username, participant.class_status,
                         ps.get_attendance_display()])
    return response


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentSession)
@require_GET
def download_experiment_metadata_participants(request, pk=None):
    experiment_metadata = get_object_or_404(ExperimentMetadata, pk=pk)

    response = HttpResponse(content_type=mimetypes.types_map['.csv'])
    response['Content-Disposition'] = 'attachment; filename={0}-participants.csv'.format(experiment_metadata.namespace)
    writer = unicodecsv.writer(response, encoding='utf-8')
    generate_participant_report(writer, experiment_metadata)
    return response


@group_required(PermissionGroup.participant)
@require_GET
def experiment_session_signup(request):
    """
    Returns and renders all the experiment session invitation that currently logged in participant has received
    """
    user = request.user
    session_unavailable = False

    upcoming_sessions = ParticipantSignup.objects.upcoming(participant=user.participant)

    invitations = Invitation.objects.upcoming(participant=user.participant) \
                                    .exclude(pk__in=upcoming_sessions.values_list('invitation__pk', flat=True))

    invitation_list = []
    for ps in upcoming_sessions:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=ps.invitation.experiment_session.pk).count()
        ps_dict = ps.to_dict(signup_count)
        invitation_list.append(ps_dict)

    for invite in invitations:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=invite.experiment_session.pk).count()
        invite_dict = invite.to_dict(signup_count)

        if invite_dict['invitation']['openings'] != 0 and session_unavailable:
            session_unavailable = False
        invitation_list.append(invite_dict)

    invitation_list = sorted(invitation_list, key=lambda use_key: use_key['invitation']['scheduled_date'])

    if session_unavailable:
        messages.error(request, _(
            """All experiment sessions are full. Signups are first-come, first-serve. Please try again later, you are
            still eligible to participate in future experiments and may receive future invitations for this
            experiment."""))

    return render(request, "subjectpool/experiment-session-signup.html", {"invitation_list": invitation_list})
