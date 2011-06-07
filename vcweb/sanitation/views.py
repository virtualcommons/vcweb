from vcweb.core.models import Experiment
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext

import logging
logger = logging.getLogger(__name__)

class QuizQuestion(object):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

q1 = QuizQuestion(type="radio", options=['Yes', 'No', 'Maybe'], sequence_number=1, answer="No")


def configure(request, experiment_id=None):
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('sanitation/configure.html', {
        'experiment': experiment,
        },
        context_instance=RequestContext(request))

def consent(request, experiment):
	logger.debug("handling consent")
	return render_to_response('sanitation/consent.html', locals(), context_instance=RequestContext(request))

def survey(request, experiment):
	logger.debug("handling survey")
	return render_to_response('sanitation/survey.html', locals(), context_instance=RequestContext(request))

def quiz(request, experiment):
	quiz_questions = [('q1', 'This is question #1?','text','answer1'), ('q2', 'This is question #2?','text','answer2')]
	logger.debug("handling quiz")
	return render_to_response('sanitation/quiz.html', locals(), context_instance=RequestContext(request))

def instructions(request, experiment):
	logger.debug("handling instructions")
	return render_to_response('sanitation/instructions.html', locals(), context_instance=RequestContext(request))

def play(request, experiment):
	logger.debug("handling play")
	return render_to_response('sanitation/play.html', locals(), context_instance=RequestContext(request))

def participate(request, experiment_id=None):
# lookup participant's current location and then invoke the method named by the location
    participant = request.user.participant
    experiment = Experiment.objects.get(pk=experiment_id)
# FIXME: this isn't implemented
    current_location = "survey"
#    current_location = participant.current_location # "consent", "survey", "quiz", "play", "instructions"
    if current_location in ["consent", "survey", "quiz", "play", "instructions"]:
        logger.debug("current location %s is valid", current_location)
# invoke current_location as a method and pass in the request and the experiment
        location_method = globals()[current_location]
        return location_method(request, experiment)
    logger.debug("Invalid location %s, redirecting to dashboard", current_location)
#    return redirect('core:dashboard')
    return render_to_response('sanitation/'+ current_location + '.html', {
        'experiment': experiment,
        },
        context_instance=RequestContext(request))
