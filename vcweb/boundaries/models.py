from django.db import models
from vcweb.core import simplecache
from vcweb.core.models import ExperimentMetadata, Parameter, ParticipantRoundDataValue
from vcweb.forestry.models import (get_harvest_decision_parameter, get_harvest_decision,
        get_regrowth_parameter, get_group_harvest_parameter)


@simplecache
def get_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='bound')

@simplecache
def get_player_status_parameter():
    return Parameter.objects.get(name='player_status')
