import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST, require_GET

from .decorators import group_required
from .forms import ChatForm, ParticipantGroupIdForm
from .http import JsonResponse, dumps
from .models import (Experiment, RoundData, get_chat_message_parameter, ExperimentConfiguration, User, PermissionGroup,
                     ParticipantGroupRelationship, ChatMessage)

logger = logging.getLogger(__name__)


SUCCESS_DICT = {'success': True}
FAILURE_DICT = {'success': False}


def _get_experiment(request, pk):
    return get_object_or_404(Experiment.objects.select_related('experimenter'), pk=pk,
                             experimenter=request.user.experimenter)


@require_POST
@group_required(PermissionGroup.experimenter)
def clone_experiment(request):
    experiment_id = request.POST.get('experiment_id')
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    experimenter = request.user.experimenter
    cloned_experiment = experiment.clone(experimenter=experimenter)
    return JsonResponse({
        'success': True,
        'experiment': cloned_experiment.to_dict(attrs=('monitor_url', 'status_line',))
    })


@require_POST
@group_required(PermissionGroup.experimenter)
def create_experiment(request):
    experiment_configuration_id = request.POST.get('experiment_configuration_id')
    experiment_configuration = get_object_or_404(ExperimentConfiguration.objects.select_related('experiment_metadata'),
                                                 pk=experiment_configuration_id)
    authentication_code = request.POST.get('authentication_code', 'test')
    experimenter = request.user.experimenter
    e = Experiment.objects.create(experimenter=experimenter, authentication_code=authentication_code,
                                  experiment_metadata=experiment_configuration.experiment_metadata,
                                  experiment_configuration=experiment_configuration)
    return JsonResponse({
        'success': True,
        'experiment': e.to_dict(attrs=('monitor_url', 'status_line',))
    })


@require_GET
def is_email_available(request):
    '''
    Returns true if the email address is not registered in our database yet. If the user is already logged in, returns
    true if the user's email is the same as the given email.
    '''
    email = request.GET.get("email").lower()
    current_user = request.user
    success = (current_user.is_authenticated() and current_user.email ==
               email) or not User.objects.filter(email=email).exists()
    logger.debug("user %s checking if email %s is available? %s", current_user, email, success)
    return JsonResponse(success if success else "That email is not available, please select another.")


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
def save_experimenter_notes(request):
    experiment_id = request.POST.get('experiment_id')
    notes = request.POST.get('notes', '')
    round_data_id = request.POST.get('round_data_id', None)
    round_data = None
    experiment = _get_experiment(request, experiment_id)
    if round_data_id is None:
        round_data = experiment.current_round_data
    else:
        round_data = get_object_or_404(RoundData, pk=round_data_id)
    current_experimenter_notes = round_data.experimenter_notes
    if notes != current_experimenter_notes:
        if current_experimenter_notes:
            experiment.log("Replace experimenter notes [%s] with [%s]" % (current_experimenter_notes, notes))
        round_data.experimenter_notes = notes
        round_data.save()
    return JsonResponse({'success': True})


@group_required(PermissionGroup.experimenter, PermissionGroup.demo_experimenter)
def get_round_data(request):
    # FIXME: naively implemented performance wise, revisit if this turns into
    # a hot spot..
    pk = request.GET.get('pk')
    round_data = get_object_or_404(RoundData.objects.select_related('experiment__experimenter'), pk=pk,
                                   experiment__experimenter=request.user.experimenter)
    group_data_values = [
        gdv.to_dict(cacheable=True)
        for gdv in round_data.group_data_value_set.select_related('group', 'parameter').all()
    ]
    participant_data_values = [
        pdv.to_dict(include_email=True, cacheable=True)
        for pdv in round_data.get_participant_data_values(is_active=True).exclude(parameter=get_chat_message_parameter())
    ]
    return JsonResponse({
        'groupDataValues': group_data_values,
        'participantDataValues': participant_data_values
    })


@login_required
@require_POST
def handle_chat_message(request, pk):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data.get('participant_group_id')
        message = form.cleaned_data.get('message')
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group'),
                                pk=participant_group_id,
                                participant=request.user.participant)
        experiment = Experiment.objects.get(pk=pk)
        current_round_data = experiment.current_round_data
        chat_message = ChatMessage.objects.create(participant_group_relationship=pgr,
                                                  string_value=message,
                                                  round_data=current_round_data)
        chat_json = chat_message.to_json()
        experiment.notify_participants(chat_json, pgr.group, notify_experimenter=True)
        return JsonResponse(SUCCESS_DICT)
    return JsonResponse(FAILURE_DICT)


@login_required
@require_GET
def check_ready_participants(request, pk=None):
    experiment = get_object_or_404(Experiment, pk=pk)
    return JsonResponse(_ready_participants_dict(experiment))


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
@require_POST
def participant_ready(request):
    form = ParticipantGroupIdForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data.get('participant_group_id')
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group__experiment'),
                                pk=participant_group_id)
        experiment = pgr.group.experiment
        round_data = experiment.current_round_data
        pgr.set_participant_ready(round_data)

        logger.debug("handling participant ready event for experiment %s", experiment)
        message = "Participant %s is ready." % request.user.participant

        experiment.notify_participants(create_message_event(message, "participant_ready"), notify_experimenter=True)
        if experiment.all_participants_ready:
            experiment.notify_experimenter(create_message_event(
                "All participants are ready to move on to the next round."))
        return JsonResponse(_ready_participants_dict(experiment))
    else:
        return JsonResponse({'success': False, 'message': "Invalid form"})


def _ready_participants_dict(experiment):
    number_of_ready_participants = experiment.number_of_ready_participants
    all_participants_ready = (number_of_ready_participants == experiment.number_of_participants)
    return {
        'success': True,
        'number_of_ready_participants': number_of_ready_participants,
        'all_participants_ready': all_participants_ready
    }


def create_message_event(message, event_type='info'):
    return dumps({'message': message, 'event_type': event_type})
