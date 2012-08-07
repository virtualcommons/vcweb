from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.views.generic import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from vcweb.core.decorators import participant_required
from vcweb.core.forms import QuizForm
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.views import ParticipantSingleExperimentMixin
from vcweb.boundaries.models import get_experiment_metadata
import logging

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    logger.debug("handling participate request for %s and experiment %s", participant, experiment_id)
    experiment = get_object_or_404(Experiment.objects.select_related(), pk=experiment_id)
    if experiment.experiment_metadata != get_experiment_metadata():
        raise Http404
    participant_experiment_relationship = participant.get_participant_experiment_relationship(experiment)
    return render_to_response(experiment.current_round_template, {
        'auth_token': participant.authentication_token,
        'participant_experiment_relationship': participant_experiment_relationship,
        'next_round_instructions': experiment.next_round_instructions
        },
        context_instance=RequestContext(request))

