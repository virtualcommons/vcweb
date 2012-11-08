from django import forms
from django.contrib import messages
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.views.generic import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from vcweb.core.decorators import participant_required
from vcweb.core.json import dumps
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.views import ParticipantSingleExperimentMixin
from vcweb.boundaries.models import get_experiment_metadata, get_regrowth_rate
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
# FIXME: this should always render the participate.html template and expose a
# JSON RoundConfiguration object to the page so the template knows what to render..?
    return render_to_response('boundaries/participate.html', {
        'auth_token': participant.authentication_token,
        'participant_experiment_relationship': participant_experiment_relationship,
        'experiment': experiment,
        'experimentModelJson': to_json(experiment),
        },
        context_instance=RequestContext(request))

def to_json(experiment):
    ec = experiment.experiment_configuration
    current_round = experiment.current_round
    experiment_model_dict = experiment.as_dict(include_round_data=False, attrs={})
    experiment_model_dict['participantsPerGroup'] = ec.max_group_size
    experiment_model_dict['numberOfRounds'] = ec.final_sequence_number
    experiment_model_dict['roundType'] = current_round.round_type
    experiment_model_dict['resourceRegenerationRate'] = get_regrowth_rate(current_round)
    return dumps(experiment_model_dict)

