from django.shortcuts import get_object_or_404, render, redirect
from vcweb.core.models import Experiment, ParticipantGroupRelationship
from vcweb.core.decorators import participant_required
from vcweb.core import dumps
from vcweb.core.http import JsonResponse
from vcweb.core.models import (is_participant, is_experimenter, Experiment, ParticipantGroupRelationship,
        ParticipantExperimentRelationship, ChatMessage, ParticipantRoundDataValue)

import random

import logging

logger = logging.getLogger(__name__)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=33)

    return render(request, 'broker/participate.html', {
	'experiment': experiment,
		 'experimentModelJson': get_view_model_json(experiment),
        })

def get_view_model_json(experiment, **kwargs):
	experiment_model_dict = experiment.as_dict();
# these are round configurations
	experiment_model_dict['thresholdGroupA'] = 5
	experiment_model_dict['thresholdGroupB'] = 5
	experiment_model_dict['chatEnabled'] = 4
	experiment_model_dict['maxHarvestDecision'] = 10
	experiment_model_dict['roundDuration'] = 10
	experiment_model_dict['networkStructure'] = 10
    
# these are round data    

    # info from last round
	experiment_model_dict['lastHarvestDecision'] = 5
	experiment_model_dict['resourceAconservation'] = 20.00
	experiment_model_dict['resourceBconservation'] = 10
	experiment_model_dict['bonusGroupA'] = 10
	experiment_model_dict['bonusGroupB'] = 10
	experiment_model_dict['bonusGlobalA'] = 10
	experiment_model_dict['bonusGlobalB'] = 10  
    

# these are experiment data
	experiment_model_dict['totalEarning'] = 100 

	experiment_model_dict['participantsPerGroup'] = 4
	experiment_model_dict['participantsPerSubGroup'] = 2
	    
	experiment_model_dict.update(**kwargs)
	return dumps(experiment_model_dict)
