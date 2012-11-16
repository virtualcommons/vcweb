from django.db import models
from vcweb.core import simplecache
from vcweb.core.models import ExperimentMetadata, Parameter, ParticipantRoundDataValue
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision, get_regrowth_rate, get_group_harvest_parameter, get_resource_level)

import logging

logger = logging.getLogger(__name__)


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='bound')

@simplecache
def get_player_status_parameter():
    return Parameter.objects.for_participant(name='player_status')

@simplecache
def get_survival_cost_parameter():
    return Parameter.objects.for_round(name='survival_cost')

@simplecache
def get_storage_parameter():
    return Parameter.objects.for_participant(name='storage')

# players can either be dead or alive
def get_player_status_dv(participant_group_relationship_id):
    return ParticipantRoundDataValue.objects.get(parameter=get_player_status_parameter(), participant_group_relationship__pk=participant_group_relationship_id)

def get_survival_cost(current_round):
    return current_round.get_parameter_value('survival_cost', default=5)

def set_storage(participant_group_relationship, value=0):
    storage_dv = participant_group_relationship.set_data_value(parameter=get_storage_parameter(), value=value)
    logger.debug("created storage variable: %s", storage_dv)
    return storage_dv

# returns the sum of all stored resources for each member in the group
def get_total_storage(group):
    # FIXME: use django queryset aggregation for this?
    return sum([pdv.value for pdv in group.get_participant_data_values(parameter=get_storage_parameter())])
