from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb import settings
from vcweb.core.forms import QuizForm
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
        return render_to_response('forestry/manage-experiment.html',
                { 'experiment': experiment },
                context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment available with id [%s]" % experiment_id)
        return redirect('core:experimenter_index')

@participant_required
def wait(request, experiment_id=None):
    try:
        experiment = Experiment.objects.get(pk=experiment_id)
        if experiment.is_round_in_progress:
            return redirect('forestry:participate', experiment_id=experiment.pk)
        else:
            return render_to_response('forestry/wait.html',
                    {'experiment': experiment},
                    context_instance=RequestContext(request))
    except Experiment.DoesNotExist:
        logger.warning("No experiment found with id %s" % experiment_id)

# FIXME: refactor this ugliness
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
                return chat(request, experiment, participant)
            elif current_round.is_quiz_round:
                return quiz(request, experiment, participant)
            else:
                # instructions or quiz round
                participant_group_rel = participant.get_participant_group_relationship(experiment)
                return render_to_response(experiment.current_round_template, {
                    'participant_group_relationship': participant_group_rel,
                    'experiment': experiment,
                    'next_round_instructions': experiment.next_round_instructions
                    },
                    context_instance=RequestContext(request))
        else:
# round is not currently active, redirect to waiting page.
            return redirect('forestry:wait', experiment_id=experiment.pk)
    except Experiment.DoesNotExist:
        error_message = "No experiment with id %s" % experiment_id
        logger.warning(error_message)
        messages.warning(request, error_message)
        return redirect('forestry:index')


import re
quiz_question_re = re.compile(r'^quiz_question_(\d+)$')
def quiz(request, experiment, participant):
    incorrect_answers = []
    if request.method == 'POST':
        form = QuizForm(request.POST)
        if form.is_valid():
# check against quiz answers (should be stored as data parameters)
            current_round = experiment.current_round
            for name, answer in form.cleaned_data.items():
                match_object = quiz_question_re.match(name)
                if match_object:
                    quiz_question_id = match_object.group
                    quiz_question = current_round.quiz_questions.get(pk=quiz_question_id)
                    if not quiz_question.is_correct(answer):
# add to wrong answers list
                        incorrect_answers.append("Your answer %s was incorrect.  The correct answer is %s. %s"
                                % (answer, quiz_question.answer,
                                    quiz_question.explanation))
    else:
        form = QuizForm(quiz_questions=experiment.quiz_questions)

    participant_group_rel = participant.get_participant_group_relationship(experiment)
    return render_to_response(experiment.current_round_template, {
        'participant_group_relationship': participant_group_rel,
        'form': form,
        'incorrect_answers': incorrect_answers
        },
        context_instance=RequestContext(request))


def chat(request, experiment, participant):
    participant_group_rel = participant.get_participant_group_relationship(experiment)
    chat_messages = experiment.current_round_data.chat_messages.filter(participant_group_relationship__group=participant_group_rel.group)
    return render_to_response(experiment.current_round_template, {
        'participant_group_relationship': participant_group_rel,
        'group': participant_group_rel.group,
        'participant': participant,
        'experiment': experiment,
        'SOCKET_IO_HOST': settings.SOCKET_IO_HOST,
        'chat_messages': chat_messages,
        },
        context_instance=RequestContext(request))


def play(request, experiment, participant):
    form = HarvestDecisionForm(request.POST or None)
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
        group = participant.groups.get(experiment=experiment)
        resource_level = get_resource_level(group)
        max_harvest_decision = get_max_harvest_decision(resource_level.value)
        resource_width = (resource_level.value / 10) * 30
        return render_to_response(experiment.current_round_template,
                locals(),
                context_instance=RequestContext(request))

