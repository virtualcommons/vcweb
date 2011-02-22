from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.decorators import participant_required, experimenter_required
from vcweb.forestry.models import get_resource_level, get_max_harvest_decision, get_forestry_experiment_metadata, set_harvest_decision
from vcweb.forestry.forms import HarvestDecisionForm

import logging
logger = logging.getLogger(__name__)

@login_required
def index(request):
    if is_participant(request.user):
        return redirect('forestry:participant_index')
        #return render_to_response('forestry/participant-index.html', RequestContext(request))
    elif is_experimenter(request.user):
        ''' FIXME: should redirect to forestry-specific experimenter dashboard instead '''
        #return render_to_response('forestry/experimenter-index.html')
        return redirect('forestry:experimenter_index')
    else:
        logger.warning("user %s isn't an experimenter or participant" % request.user)
        return redirect('home')

@experimenter_required
def experimenter_index(request):
    experimenter = request.user.experimenter
    experiments = experimenter.experiments.all()
    return render_to_response('forestry/experimenter-index.html', locals(), context_instance=RequestContext(request))

@participant_required
def participant_index(request):
    participant = request.user.participant
    experiment_dict = {}
    for experiment in participant.experiments.filter(experiment_metadata=get_forestry_experiment_metadata()):
        status = experiment.get_status_display()
        logger.debug("status is %s" % status)
        if not status in experiment_dict:
            experiment_dict[status] = list()
        experiment_dict[status].append(experiment)

    return render_to_response('forestry/participant-index.html', locals(), context_instance=RequestContext(request))

@experimenter_required
def configure(request):
    return Http404()

@experimenter_required
def manage_experiment(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/manage-experiment.html', locals(), context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment available with id [%s]" % experiment_id)
        return redirect('core:experimenter_index')

@participant_required
def wait(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        return render_to_response('forestry/wait.html',
                locals(),
                context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment found with id %s" % experiment_id)

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        if experiment.is_round_in_progress:
            current_round = experiment.current_round
            if current_round.has_data_parameters:
                return play(request, experiment, participant)
            elif current_round.is_chat_round:
                group = participant.groups.get(experiment=experiment)
                from vcweb import settings
                return render_to_response(experiment.current_round_template,
                        {'group': group, 'participant': participant, 'experiment': experiment, 'SOCKET_IO_HOST': settings.SOCKET_IO_HOST},
                        context_instance=RequestContext(request))
            else:
                # instructions or quiz round
                return render_to_response(experiment.current_round_template,
                        locals(),
                        context_instance=RequestContext(request))
        else:
# round is not currently active, redirect to waiting page.
            return redirect('forestry:wait', experiment_id=experiment.pk)
    except Experiment.DoesNotExist:
        error_message = "No experiment with id %s" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
        return redirect('forestry:index')

def play(request, experiment, participant):
    if request.method == 'POST':
        # process harvest decision
        form = HarvestDecisionForm(request.POST)
        if form.is_valid():
            harvest_decision = form.cleaned_data['harvest_decision']
            resource_level = get_resource_level(participant.get_group(experiment))
            max_harvest_decision = get_max_harvest_decision(resource_level.value)
            if harvest_decision <= max_harvest_decision:
                set_harvest_decision(participant=participant, experiment=experiment, value=harvest_decision)
                return redirect('forestry:wait', experiment_id=experiment.pk)
            else:
                raise forms.ValidationError("invalid harvest decision %s > max %s" % (harvest_decision, max_harvest_decision))
    else:
        form = HarvestDecisionForm()
        group = participant.groups.get(experiment=experiment)
        resource_level = get_resource_level(group)
        logger.debug("resource level is: %s" % resource_level)
        max_harvest_decision = get_max_harvest_decision(resource_level.value)
        logger.debug("max harvest decision: %s" % max_harvest_decision)
        resource_width = (resource_level.value / 10) * 30
    return render_to_response(experiment.current_round_template,
            locals(),
            context_instance=RequestContext(request))

