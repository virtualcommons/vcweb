from django.shortcuts import render
from vcweb.core.decorators import participant_required

import logging

logger = logging.getLogger(__name__)

# Create your views here.

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)
    if experiment.experiment_metadata != get_experiment_metadata():
        raise Http404
    return render(request, experiment.participant_template,
            experiment.template_context(participant_group_relationship=pgr, experimentModelJson=get_view_model_json(experiment,pgr)))


def get_view_model(request, experiment_id=None):
    pass

def control_gate(request, experiment_id=None):
    pass
