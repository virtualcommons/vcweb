from django.shortcuts import render
from vcweb.core.decorators import participant_required

import logging

logger = logging.getLogger(__name__)

class ViewModel(object):

    def __init__(self, participant_group_relationship, experiment=None, round_data=None, **kwargs):
        self.participant_group_relationship = participant_group_relationship
        self.group = participant_group_relationship.group

    def to_json(self):
        return dumps({
            'pid': self.participant_group_relationship.pk

            })


@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'), pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(participant)
    if experiment.experiment_metadata != get_experiment_metadata():
        raise Http404
    return render(request, experiment.participant_template,
            experiment.template_context(participant_group_relationship=pgr, 
                experimentModelJson=ViewModel(pgr, experiment=experiment).to_json()))


@participant_required
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'),
                                   pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(request.user.participant)
    return JsonResponse(ViewModel(pgr, experiment=experiment).to_json())


@participant_required
def control_gate(request, experiment_id=None):
    pass
