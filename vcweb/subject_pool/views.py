from django.contrib import messages
from django.forms.models import modelformset_factory
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _
from vcweb import settings
from vcweb.core.models import (ExperimentSession, ExperimentMetadata, Participant, ParticipantSignup, Invitation,
                               Institution, send_email)
from vcweb.core.decorators import experimenter_required, participant_required
from datetime import datetime, time, timedelta
from time import mktime
from vcweb.core import dumps
from vcweb.core.http import JsonResponse
from django.core.mail import EmailMultiAlternatives

from forms import SessionForm, SessionInviteForm, ParticipantAttendanceForm

import markdown

import random
import logging

logger = logging.getLogger(__name__)


@experimenter_required
def session_list_view(request):
    """
    Returns by rendering the Subject Recruitment page with all the active experiment sessions and past experiment
    sessions.
    """
    experimenter = request.user.experimenter
    data = ExperimentSession.objects.filter(creator=request.user)
    experiment_metadata_list = [em.to_dict() for em in ExperimentMetadata.objects.bookmarked(experimenter)]

    session_list = [session.to_dict() for session in data]

    session_data = {
        "session_list": session_list,
        "experiment_metadata_list": experiment_metadata_list
    }

    form = SessionInviteForm()

    return render(request, "subject-pool/experimenter-index.html",
                  {"view_model_json": dumps(session_data), "form": form})


@experimenter_required
def update_session(request):
    """
    Depending upon the type of request, this view method can be used to create, update or delete Experiment sessions.
    """
    user = request.user
    form = SessionForm(request.POST or None)
    if form.is_valid():
        # if the form is valid get the experiment_session pk
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

    message = '''<div class="alert alert-danger alert-dismissable alert-link">
                   <button class=close data-dismiss=alert aria-hidden=true>
                   &times;</button>{errors}</div>\n
                '''.format(errors='\n'.join(['<p>{e}</p>'.format(e=e) for e in form.non_field_errors()]))

    return JsonResponse(dumps({
        'success': False,
        'message': message
    }))


@experimenter_required
def get_session_events(request):
    """
    Returns the list of Experiment sessions that fall within the given range,
    Used by calendar on he subject recruitment page to display experiment sessions falling in that period.
    """
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


def get_invitations_count(request):
    """
    API endpoint that returns the potential participant count based on the selected experiment metadata and Institution
    """

    session_pk_list = request.POST.get('session_pk_list').split(",")
    affiliated_university = request.POST.get('affiliated_university')

    experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
    experiment_metadata_pk_list = experiment_sessions.values_list('experiment_metadata__pk', flat=True)

    if len(set(experiment_metadata_pk_list)) == 1:
        # get the experiment metadata pk of any session,
        # as all sessions selected by experimenter to send invitations belong to same experiment metadata
        # (This is ensured as it is a constraint)
        experiment_metadata_pk = experiment_metadata_pk_list[0]

        only_undergrad = request.POST.get('only_undergrad')

        potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_university,
                                                            only_undergrad=only_undergrad)
        return JsonResponse(dumps({
            'success': True,
            'invitesCount': len(potential_participants)
        }))
    else:
        return JsonResponse(dumps({
            'success': False,
            'invitesCount': 0
        }))


def get_invitation_email_content(custom_invitation_text, experiment_session_ids):
    plaintext_template = get_template('subject-pool/email/invitation-email.txt')
    c = Context({
        'invitation_text': custom_invitation_text,
        'session_list': ExperimentSession.objects.filter(pk__in=experiment_session_ids),
    })
    plaintext_content = plaintext_template.render(c)
    html_content = markdown.markdown(plaintext_content)
    logger.debug("plaintext_content %s, html_content %s", plaintext_content, html_content)
    return plaintext_content, html_content


@experimenter_required
def send_invitations(request):
    """
    Sends out invitation emails to random participants which match the required invitation criteria,
    using the provided email subject and message. Also returns the total number of invites sent.
    """
    user = request.user
    form = SessionInviteForm(request.POST or None)
    # Default Message
    message = "Please fill in all the details of the invitation form"
    if form.is_valid():
        invitation_subject = form.cleaned_data.get('invitation_subject')
        invitation_text = form.cleaned_data.get('invitation_text')
        # use currently logged in experimenter as the sender of the invitations.
        from_email = user.email

        session_pk_list = request.POST.get('session_pk_list').split(",")
        invitation_count = form.cleaned_data.get('no_of_people')
        affiliated_university = form.cleaned_data.get('affiliated_university')

        experiment_sessions = ExperimentSession.objects.filter(pk__in=session_pk_list)
        experiment_metadata_pk_list = experiment_sessions.values_list('experiment_metadata__pk', flat=True)

        if len(set(experiment_metadata_pk_list)) == 1:
            # get the experiment metadata pk of any session, as all sessions selected by experimenter to send invitations
            # belong to same experiment metadata(This is ensured as it is a constraint)
            experiment_metadata_pk = experiment_metadata_pk_list[0]

            potential_participants = get_potential_participants(experiment_metadata_pk, affiliated_university,
                                                                only_undergrad=form.cleaned_data.get('only_undergrad'))
            potential_participants_count = len(potential_participants)

            final_participants = None

            if potential_participants_count == 0:
                final_participants = []
                message = "There are no more eligible participants that can be invited for this experiment."
            else:
                if potential_participants_count < invitation_count:
                    # less candidate participants than the number of requested participants, use them all
                    final_participants = potential_participants
                else:
                    final_participants = random.sample(potential_participants, invitation_count)
                message = "Your invitations were sent to %s / %s participants." % (
                    len(final_participants), invitation_count)

                today = datetime.now()
                invitations = []
                recipient_list = []
                for participant in final_participants:
                    recipient_list.append(participant.email)
                    for es in experiment_sessions:
                        invitations.append(
                            Invitation(participant=participant, experiment_session=es, date_created=today,
                                       sender=user))
                Invitation.objects.bulk_create(invitations)

                plaintext_content, html_content = get_invitation_email_content(invitation_text, session_pk_list)

                msg = EmailMultiAlternatives(subject=invitation_subject,
                                             body=plaintext_content,
                                             from_email=from_email,
                                             to=[from_email],
                                             bcc=recipient_list,
                                             cc=['allen.lee@asu.edu'])
                msg.attach_alternative(html_content, "text/html")

                msg.send()

            return JsonResponse(dumps({
                'success': True,
                'message': message,
                'invitesCount': len(final_participants)
            }))
        else:
            message = "To Invite Participants Please Select Experiment Sessions of same Experiment"
            return JsonResponse(dumps({
                'success': False,
                'message': message
            }))
    else:
        # Form is not valid
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def invite_email_preview(request):
    """
    Generates email Preview for the provided invitation details
    """
    form = SessionInviteForm(request.POST or None)
    message = "Please fill in all form fields to preview email"
    if form.is_valid():
        invitation_text = form.cleaned_data.get('invitation_text')
        session_pk_list = request.POST.get('session_pk_list').split(",")
        plaintext_content, html_content = get_invitation_email_content(invitation_text, session_pk_list)
        return JsonResponse(dumps({
            'success': True,
            'content': html_content
        }))
    else:
        # Form is not Valid
        return JsonResponse(dumps({
            'success': False,
            'message': message
        }))


def get_potential_participants(experiment_metadata_pk, institution="Arizona State University", days_threshold=7,
                               only_undergrad=True):
    """
    Returns the pool of participants which match the required invitation criteria.
    """

    try:
        affiliated_institution = Institution.objects.get(name=institution)
    except Institution.DoesNotExist:
        affiliated_institution = None

    if affiliated_institution:
        # Get unlikely participants for the given parameters
        excluded_participants = get_excluded_participants(days_threshold, experiment_metadata_pk)
        if only_undergrad:
            potential_participants = Participant.objects.filter(can_receive_invitations=True,
                                                                institution=affiliated_institution,
                                                                class_status__in=Participant.UNDERGRADUATE_CLASS_CHOICES) \
                .exclude(pk__in=excluded_participants)
        else:
            potential_participants = Participant.objects.filter(can_receive_invitations=True,
                                                                institution=affiliated_institution) \
                .exclude(pk__in=excluded_participants)
    else:
        potential_participants = []
    return potential_participants


def get_excluded_participants(days_threshold, experiment_metadata_pk):
    """
    Returns the pool of participants which do not match the required invitation criteria.
    """
    last_week_date = datetime.now() - timedelta(days=days_threshold)
    # invited_in_last_threshold_days contains all Invitations that were generated in last threshold days for the
    # given Experiment metadata
    invited_in_last_threshold_days = Invitation.objects \
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
    """
    Performs Update or Get operation on the ParticipantSignup model depending upon the request.
    If request is GET, then the function will return the attendance formset. If request is POST then
    the function will update the Participant Attendance and return the updated formset.
    """
    attendanceformset = modelformset_factory(ParticipantSignup, form=ParticipantAttendanceForm,
                                             exclude=('date_created',), extra=0)
    es = ExperimentSession.objects.get(pk=pk)
    invitations_sent = Invitation.objects.filter(experiment_session=es)
    session_detail = {'experiment_metadata': es.experiment_metadata, 'start_date': es.scheduled_date.date(),
                      'start_time': es.scheduled_date.strftime('%I:%M %p'), 'end_date': es.scheduled_end_date.date(),
                      'end_time': es.scheduled_end_date.strftime('%I:%M %p'), 'location': es.location,
                      'capacity': es.capacity}

    if request.method == "POST":
        formset = attendanceformset(request.POST,
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
        formset = attendanceformset(queryset=ParticipantSignup.objects.filter(invitation__in=invitations_sent))

    return render(request, 'subject-pool/session_detail.html', {'session_detail': session_detail, 'formset': formset})


@participant_required
def experiment_session_signup(request):
    user = request.user
    logger.debug(user)
    if request.method == 'POST':
        data = dict(request.POST.iteritems())
        logger.debug(data)
        invitation_pk = None
        experiment_metadata_pk = None

        for key in data:
            if key != 'experiment_metadata_pk':
                invitation_pk = int(data[key])  # the key is the experiment Metadata Name
            else:
                experiment_metadata_pk = int(data[key])

        if experiment_metadata_pk is not None:
            invitation = Invitation.objects.select_related('experiment_session').get(pk=invitation_pk)
            # lock on the experiment session to prevent concurrent participant signups for an experiment session
            # exceeding its capacity
            lock = ExperimentSession.objects.select_for_update().get(pk=invitation.experiment_session.pk)
            signup_count = ParticipantSignup.objects.filter(
                invitation__experiment_session__pk=invitation.experiment_session.pk).count()

            try:
                ps = ParticipantSignup.objects.get(
                    invitation__participant=user.participant,
                    invitation__experiment_session__experiment_metadata__pk=experiment_metadata_pk,
                    attendance=ParticipantSignup.ATTENDANCE.registered)
            except ParticipantSignup.DoesNotExist:
                ps = ParticipantSignup()

            success = False
            # verify that still there is vacancy for the selected experiment session
            if signup_count < invitation.experiment_session.capacity:
                ps.invitation = invitation
                ps.date_created = datetime.now()
                ps.attendance = ParticipantSignup.ATTENDANCE.registered
                ps.save()
                success = True
            else:
                # No vacancy
                # set success to true if the user is already registered for the same experiment session
                # else set it to false
                success = (ps.invitation.pk == invitation_pk)

            # release the lock
            lock.save()

            new_list, flag = get_participant_invitations(user)

            if success:
                messages.add_message(request, messages.SUCCESS, _(
                    "Thanks, you have successfully registered for this experiment session. A Confirmation email has been sent to you. Please remember to be on time!"))

                send_email("subject-pool/email/confirmation-email.txt", {'session': lock}, "Confirmation Email",
                           settings.SERVER_EMAIL,
                           [user.email])
            else:
                messages.add_message(request, messages.ERROR, _(
                    "Sorry, you were not able to register for the given experiment session. Signups are first-come first-serve, please try again next time as you will still be eligible to participate in future experiments."))

            return render(request, "participant/experiment-session-signup.html",
                          {"invitation_list": new_list})

        else:
            # ParticipantSignup.objects \
            #     .select_related('invitation', 'invitation__experiment_session__experiment_metadata') \
            #     .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.registered,
            #             invitation__experiment_session__experiment_metadata__pk=experiment_metadata_pk).delete()

            # unregister a user from the experiment_session
            try:
                ParticipantSignup.objects.\
                    select_related('invitation', 'invitation__participant').\
                    get(invitation__participant__user=user, invitation__pk=invitation_pk).delete()
                messages.success(request, _(
                    "Thanks, you have successfully unregistered yourself from the experiment session."))

            except ParticipantSignup.DoesNotExist:
                logger.debug("Could't unregister user as participant signup with invitation_pk = %s don't exist",
                             invitation_pk)
                messages.success(request, _(
                    "Sorry, Something bad happened and we were not able to unregister you from the experiment session. Please try again. If the problem persists please file an issue"))

            return JsonResponse(dumps({
                'success': True
            }))

    elif request.method == "GET":
        new_list, flag = get_participant_invitations(user)

        if flag:
            messages.error(request, _(
                "Sorry, all the experiment sessions are full. Signups are first-come, first-serve. Please try again next time, you will still be eligible to participate in future experiments."))

        return render(request, "participant/experiment-session-signup.html",
                      {"invitation_list": new_list})


def get_participant_invitations(user):
    flag = False
    # If the Experiment Session is being conducted tomorrow then don't show invitation to user
    tomorrow = datetime.now() + timedelta(days=1)

    active_experiment_sessions = ParticipantSignup.objects \
        .select_related('invitation', 'invitation__experiment_session') \
        .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.registered,
                invitation__experiment_session__scheduled_date__gt=tomorrow)

    # Making sure that user don't see invitations for a experiment for which he has already participated
    # useful in cases when the experiment has lots of sessions spanning to lots of days. It avoids a user to participate
    # in another experiment session after attending one of the experiment session of same experiment in last couple
    # of days
    participated_experiment_metadata = ParticipantSignup.objects \
        .select_related('invitation', 'invitation__experiment_session',
                        'invitation__experiment_session__experiment_metadata') \
        .filter(invitation__participant=user.participant, attendance=ParticipantSignup.ATTENDANCE.participated)

    participated_experiment_metadata_pk_list = [ps.invitation.experiment_session.experiment_metadata.pk for ps in
                                                participated_experiment_metadata]
    # logger.debug(participated_experiment_metadata_pk_list)
    active_invitation_pk_list = [ps.invitation.pk for ps in active_experiment_sessions]
    # logger.debug(active_invitation_pk_list)
    invitations = Invitation.objects.select_related('experiment_session', 'experiment_session__experiment_metadata__pk') \
        .filter(participant=user.participant, experiment_session__scheduled_date__gt=tomorrow) \
        .exclude(experiment_session__experiment_metadata__pk__in=participated_experiment_metadata_pk_list) \
        .exclude(pk__in=active_invitation_pk_list)

    # logger.debug(invitations)
    invitation_list = []
    for ps in active_experiment_sessions:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=ps.invitation.experiment_session.pk).count()
        ps_dict = ps.to_dict(signup_count)
        invitation_list.append(ps_dict)

    for invite in invitations:
        signup_count = ParticipantSignup.objects.filter(
            invitation__experiment_session__pk=invite.experiment_session.pk).count()
        invite_dict = invite.to_dict(signup_count)
        logger.debug(invite_dict)
        logger.debug(invite_dict['invitation']['openings'])
        if invite_dict['invitation']['openings'] and flag:
            flag = False
        invitation_list.append(invite_dict)

    new_list = sorted(invitation_list, key=lambda use_key: use_key['invitation']['scheduled_date'])

    return new_list, flag
