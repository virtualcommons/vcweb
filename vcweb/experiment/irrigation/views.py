import logging

from django.shortcuts import render, get_object_or_404

from vcweb.core.decorators import group_required
from vcweb.core.http import JsonResponse, dumps
from vcweb.core.models import Experiment, PermissionGroup
from vcweb.experiment.irrigation.services import get_experiment_metadata

logger = logging.getLogger(__name__)


class ViewModel(object):

    experiment_model_defaults = {
        'submitted': False,
        'chatEnabled': False,
        'storage': 0,
    }

    def __init__(self, participant_group_relationship, experiment=None, **kwargs):
        self.participant_group_relationship = participant_group_relationship
        self.group = participant_group_relationship.group
        self.experiment = self.group.experiment if experiment is None else experiment
        self.current_round_data = self.experiment.current_round_data
        self.current_round = self.current_round_data.round_configuration
        self.experiment_model = self.experiment.to_dict(include_round_data=False,
                                                        default_value_dict=ViewModel.experiment_model_defaults)

    def to_dict(self):
        current_round = self.experiment.current_round
        self.experiment_model.update(
            pid=self.participant_group_relationship.pk,
            templateName=current_round.template_name,
        )
        return self.experiment_model

    def to_json(self):
        return dumps(self.to_dict())


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'),
                                   pk=experiment_id,
                                   experiment_metadata=get_experiment_metadata())
    pgr = experiment.get_participant_group_relationship(participant)
    return render(request, experiment.participant_template,
                  experiment.template_context(pgr, experimentModelJson=ViewModel(pgr, experiment=experiment).to_json()))


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def get_view_model(request, experiment_id=None):
    experiment = get_object_or_404(Experiment.objects.select_related('experiment_metadata', 'experiment_configuration'),
                                   pk=experiment_id)
    pgr = experiment.get_participant_group_relationship(
        request.user.participant)
    return JsonResponse(ViewModel(pgr, experiment=experiment).to_dict())


@group_required(PermissionGroup.participant, PermissionGroup.demo_participant)
def control_gate(request, experiment_id=None):
    pass
