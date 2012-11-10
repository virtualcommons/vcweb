from django.db import models
from vcweb.core import simplecache
from vcweb.core.models import ExperimentMetadata, Parameter, ParticipantRoundDataValue
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision, get_regrowth_rate, get_group_harvest_parameter)


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='bound')

@simplecache
def get_player_status_parameter():
    return Parameter.objects.for_participant(name='player_status')

@simplecache
def get_survival_cost_parameter():
    return Parameter.objects.for_round(name='survival_cost')

# players can either be dead or alive
def get_player_status_dv(participant_group_relationship_id):
    return ParticipantRoundDataValue.objects.get(parameter=get_player_status_parameter(), participant_group_relationship__pk=participant_group_relationship_id)

def get_survival_cost(current_round):
    return current_round.get_parameter_value('survival_cost', default=5)


