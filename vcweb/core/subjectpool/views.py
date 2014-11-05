from datetime import datetime, timedelta
from time import mktime
import itertools
import logging
import random
import unicodecsv
import markdown

from django.core.mail import EmailMultiAlternatives
from django.db import transaction

from django.template import Context
from django.template.loader import get_template
from django.forms.models import modelformset_factory
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from vcweb.core.subjectpool.forms import (
    SessionInviteForm, ExperimentSessionForm, ParticipantAttendanceForm, CancelSignupForm)
from vcweb.core.views import mimetypes

from vcweb.core.models import (
    ExperimentSession, ExperimentMetadata, Invitation, send_email)
from vcweb.core.http import JsonResponse, dumps
from vcweb.core.decorators import group_required, ownership_required
from vcweb.core.models import (
    Participant, Institution, ParticipantSignup, PermissionGroup)


logger = logging.getLogger(__name__)


@group_required(PermissionGroup.experimenter)
@require_GET
def experimenter_index(request):
    """
    Provides experimenter subject recruitment interface with all active experiment sessions and past experiment
    sessions.
    """
    experimenter = request.user.experimenter
    data = ExperimentSession.objects.filter(creator=request.user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]
    session_list = [session.to_dict() for session in data]
    potential_participants_count = Participant.objects.active().count()
    session_data = {
        "session_list": session_list,
        "experiment_metadata_list": experiment_metadata_list,
        'allEligibleParticipants': potential_participants_count,
        'potentialParticipantsCount': potential_participants_count,
    }
    form = SessionInviteForm()
    return render(request, "experimenter/subject-pool-index.html",
                  {"view_model_json": dumps(session_data), "form": form})


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
    if isinstance(timestamp, (str, unicode)):

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

    session_pk_list = request.POST.get('session_pk_list').split(",")
    affiliated_institution = request.POST.get('affiliated_institution')

    experiment_sessions = ExperimentSession.objects.filter(
        pk__in=session_pk_list)
    experiment_metadata_pk_list = experiment_sessions.values_list(
        'experiment_metadata__pk', flat=True)

    if len(set(experiment_metadata_pk_list)) == 1:
        # As all sessions selected by experimenter to send invitations belong to same experiment metadata
        # get the experiment metadata pk of any session (This is ensured as it
        # is a constraint)
        experiment_metadata_pk = experiment_metadata_pk_list[0]

        only_undergrad = request.POST.get('only_undergrad')

        potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_institution,
                                                            only_undergrad=only_undergrad)
        return JsonResponse({
            'success': True,
            'invitesCount': len(potential_participants)
        })
    else:
        return JsonResponse({
            'success': False,
            'invitesCount': 0
        })


def get_invitation_email_content(custom_invitation_text, experiment_session_ids):
    plaintext_template = get_template('email/invitation-email.txt')
    c = Context({
        'invitation_text': custom_invitation_text,
        'session_list': ExperimentSession.objects.filter(pk__in=experiment_session_ids),
        'SITE_URL': settings.SITE_URL,
    })
    plaintext_content = plaintext_template.render(c)
    html_content = markdown.markdown(plaintext_content)

    return plaintext_content, html_content


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
            # get the experiment metadata pk of any session, as all sessions selected by experimenter to send invitations
            # belong to same experiment metadata (This has to be ensured as it is a constraint)
            experiment_metadata_pk = experiment_metadata_pk_list[0]

            potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_institution,
                                                                only_undergrad=form.cleaned_data.get('only_undergrad'))
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
                message = "Your invitations were sent to %s / %s participants." % (len(final_participants), invitation_count)

                today = datetime.now()
                invitations = []
                recipient_list = [settings.SERVER_EMAIL]
                for participant in final_participants:
                    recipient_list.append(participant.email)
                    for es in experiment_sessions:
                        invitations.append(Invitation(participant=participant, experiment_session=es, date_created=today, sender=user))
                Invitation.objects.bulk_create(invitations)

                plaintext_content, html_content = get_invitation_email_content(invitation_text, session_pk_list)

                msg = EmailMultiAlternatives(subject=invitation_subject, body=plaintext_content, from_email=from_email,
                                             to=[from_email], bcc=recipient_list)
                msg.attach_alternative(html_content, "text/html")
                msg.send()

            return JsonResponse({
                'success': True,
                'message': message,
                'invitesCount': len(final_participants)
            })
        else:
            message = "To Invite Participants Please Select Experiment Sessions of same Experiment"
            return JsonResponse({
                'success': False,
                'message': message
            })
    else:
        # Form is not valid
        return JsonResponse({ 'success': False, 'errors': form.errors })


@group_required(PermissionGroup.experimenter)
@require_POST
def invite_email_preview(request):
    """
    Generates email Preview for the provided invitation details
    """
    form = SessionInviteForm(request.POST or None)
    message = "Please fill in all the form fields to preview the invitation email."
    if form.is_valid():
        invitation_text = form.cleaned_data.get('invitation_text')
        session_pk_list = request.POST.get('session_pk_list').split(",")
        plaintext_content, html_content = get_invitation_email_content(
            invitation_text, session_pk_list)
        return JsonResponse({
            'success': True,
            'content': html_content
        })
    else:
        # Form is not Valid
        return JsonResponse({
            'success': False,
            'message': message
        })


def get_potential_participants(experiment_metadata_pk, institution="Arizona State University", only_undergrad=True):
    """
    Returns the pool of participants which match the required invitation criteria.
    """
    # Get excluded participants for the given parameters
    excluded_participants = get_excluded_participants(experiment_metadata_pk)
    return Participant.objects.invitation_eligible(only_undergrad=only_undergrad, institution=institution) \
            .exclude(pk__in=excluded_participants)


def get_excluded_participants(experiment_metadata_pk):
    """
    Returns the pool of participants which do not match the required invitation criteria.
    """
    # invited_in_last_threshold_days contains all Invitations that were generated in last threshold days for the
    # given Experiment metadata
    invited_in_last_threshold_days = Invitation.objects.already_invited(experiment_metadata_pk=experiment_metadata_pk) \
            .values_list('participant__pk', flat=True)

    # signup_participants is the list of participants who has already participated in the
    # given Experiment Metadata(in the past or currently participating)
    signup_participants = ParticipantSignup.objects.registered(experiment_metadata_pk=experiment_metadata_pk) \
            .values_list('invitation__participant__pk', flat=True)

    invalid_participants = Participant.objects.invalid_participants().values_list('pk', flat=True)
    # returns a list of participant pks who have already received invitations in last threshold days, have already
    # participated in the same experiment, or have 'mailinator.com' in their
    # name
    return list(set(itertools.chain(invited_in_last_threshold_days, signup_participants, invalid_participants)))


@group_required(PermissionGroup.experimenter)
@ownership_required(ExperimentSession)
def manage_participant_attendance(request, pk=None):
    """
    Performs Update or Get operation on the ParticipantSignup model depending upon the request.
    If request is GET, then the function will return the attendance formset. If request is POST then
    the function will update the Participant Attendance and return the updated formset.
    """
    es = ExperimentSession.objects.get(pk=pk)

    invitations_sent = Invitation.objects.filter(experiment_session=es)
    session_detail = dict(pk=es.pk, experiment_metadata=es.experiment_metadata, start_date=es.scheduled_date.date(),
                          start_time=es.scheduled_date.strftime('%I:%M %p'), end_date=es.scheduled_end_date.date(),
                          end_time=es.scheduled_end_date.strftime('%I:%M %p'), location=es.location,
                          capacity=es.capacity)

    attendanceformset = modelformset_factory(ParticipantSignup, form=ParticipantAttendanceForm,
                                             exclude=('date_created',), extra=0)

    if request.method == "POST":
        formset = attendanceformset(request.POST,
                                    queryset=ParticipantSignup.objects.select_related(
                                        'invitation__participant__user').
                                    filter(invitation__in=invitations_sent))
        if formset.is_valid():
            messages.add_message(
                request, messages.SUCCESS, 'Well done...Your changes were successfully saved.')
            if formset.has_changed():
                formset.save()
        else:
            messages.add_message(request, messages.ERROR,
                                 'Something went wrong...Your changes were not saved. Please try again')
    else:
        formset = attendanceformset(
            queryset=ParticipantSignup.objects.select_related('invitation__participant__user').
            filter(invitation__in=invitations_sent))

    return render(request, 'experimenter/session_detail.html',
                  {'session_detail': session_detail, 'formset': formset})


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
            messages.add_message(request, messages.SUCCESS,
                                 _("You are no longer signed up for %s - thanks for letting us know!" % es))
        else:
            logger.error(
                "Invalid request: Participant %s tried to cancel signup %s", request.user.participant, signup)
            messages.add_message(request, messages.ERROR, _(
                "You don't appear to be signed up for this session."))
    else:
        messages.add_message(
            request, messages.ERROR, _("Sorry, we couldn't process your request"))
    return redirect('core:dashboard')


@group_required(PermissionGroup.participant)
@require_POST
def submit_experiment_session_signup(request):
    """
    Enrolls the currently logged in user in the selected experiment session.
    """
    user = request.user
    invitation_pk = request.POST.get('invitation_pk')
    invitation = get_object_or_404(Invitation.objects.select_related('experiment_session'), pk=invitation_pk)
    registered = False
    waitlist = False
    attendance = ParticipantSignup.ATTENDANCE.registered
    message = ""

    # lock on the experiment session to prevent concurrent participant signups for an experiment session
    # exceeding its capacity
    with transaction.atomic():
        participant_signups = ParticipantSignup.objects.select_for_update().registered(experiment_session_pk=invitation.experiment_session_id)
        signup_count = participant_signups.count()
        # verify for the vacancy in the selected experiment session before
        # creating participant signup entry
        if signup_count < invitation.experiment_session.capacity:
            registered = True
            message = '''You are now registered for this experiment session. A confirmation email has been sent and you
            should also receive a reminder email one day before the session. Thanks in advance for participating!'''
        else:
            # signups are full, check if waitlists are full
            waitlist_count = ParticipantSignup.objects.waitlist(experiment_session_pk=invitation.experiment_session_id).count()
            if waitlist_count < settings.SUBJECT_POOL_WAITLIST_SIZE:
                waitlist = True
                attendance = ParticipantSignup.ATTENDANCE.waitlist
                message = """This experiment session is currently full, but you have been added to the waitlist. You may
                still be able to participate in this experiment if other participants leave the experiment."""
        ps, created = ParticipantSignup.objects.get_or_create(invitation=invitation, attendance=attendance)
        logger.debug("updated participant signup %s - created? %s", ps, created)

    if registered or waitlist:
        messages.success(request, _(message))
        send_email("email/confirmation-email.txt", {'session': invitation.experiment_session}, "Confirmation Email",
                   settings.SERVER_EMAIL, [user.email])
        return redirect('core:dashboard')
    else:
        messages.error(request, _("This session is currently full. Please select a different session or try again later to see if any slots have opened up. Thank you for your interest!"))
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
    for ps in ParticipantSignup.objects.select_related('invitation__participant').filter(
            invitation__experiment_session=experiment_session):
        participant = ps.invitation.participant
        writer.writerow([participant.email, participant.full_name, participant.username, participant.class_status,
                         ps.attendance])
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

    return render(request, "participant/experiment-session-signup.html", {"invitation_list": invitation_list, 'waitlist_size': settings.SUBJECT_POOL_WAITLIST_SIZE})
