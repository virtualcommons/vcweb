# importing external methods and classes
from vcweb.core.models import Experiment
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
import logging
import random


#Globals
logger = logging.getLogger(__name__)
symbol = '@'
growth_rate = 'hourly'
consent = ['Introduction to Global Health Class', symbol,'one week', growth_rate]

# "consent", "survey", "quiz", "play", "instructions"
current_location = "consent"

treatment = "In-group"
resource = "Sanitation is vital for health: Readers of a prestigious medical journal were recently asked to name the greatest medical advance in the last century and a half. The result: better sanitation. In nineteenth-century Europe and North America, diarrhoea, cholera, and typhoid spread through poor sanitation was the leading cause of childhood illness and death; today, such deaths are rare in these regions. In developing countries, however, they are all too common, and recent research suggests that poor sanitation and hygiene are either the chief or the underlying cause in over half of the annual 10 million child deaths. Compelling, evidence-based analysis shows that hygiene and sanitation are among the most cost-effective public health interventions to reduce childhood mortality. Access to a toilet alone can reduce child diarrhoeal deaths by over 30 percent, and hand-washing by more than 40 percent."

r = len(resource) + 1
resource_index = range(1,r)
pollution_amount = random.randint(1,200)

pollution = random.sample(resource_index, pollution_amount) 


game_state = ""
for i, char in  enumerate(resource):
	if i in pollution:
		symbol_url = str("" + symbol + "")
		game_state = game_state + symbol_url
	game_state = game_state + char


# Additional Classes #FIXME move to  external file
class QuizQuestion(object):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

q = str("Is it better to have more or less " + symbol + " symbols in your text?")
q1 = QuizQuestion(type="radio", options=['More', 'Less'], sequence_number=1, answer="No", question=q)

q = str("" + symbol + "")
q2 = QuizQuestion(type="radio", options=['More', 'Less'], sequence_number=2, answer="Less", question=q)

q = str("When is the text clean?")
q3 = QuizQuestion(type="radio", options=['When there are no symbols in it.', 'It is always clean', 'When there are lots of symbols.'], sequence_number=3, answer="When there are no symbols in it", question=q)

q = str("How often is more 'pollution' added in the form of "+symbol+" symbols?")
q4 = QuizQuestion(type="radio", options=['Randomly', growth_rate , 'When someone logs on'], sequence_number=4, answer="No", question=q)

q = str("Does the amount of symbols added "+growth_rate+" determine how much 'pollution is added?'")
q5 = QuizQuestion(type="radio", options=['Yes', 'No'], sequence_number=5, answer="Yes", question=q)

q = str("What do you do if there is no pollution to clean?")
q6 = QuizQuestion(type="radio", options=['You are done with the experiment', 'Come back later', 'Pollute the text'], sequence_number=6, answer="Come back later", question=q)

q = str("How do you earn extra-credit points?")
q7 = QuizQuestion(type="radio", options=['Polluting the text', 'Keeping the text clean', 'Posting messages to my group'], sequence_number=7, answer="No", question=q)





class SurveyQuestion(object):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)
s1 = SurveyQuestion(type="radio", options=['Male', 'Female'], sequence_number=1, size="", question="gender")
s2 = SurveyQuestion(type="text", options=['MM-DD-YYYY'], sequence_number=2, size="4", question="What year were you born?")
s3 = SurveyQuestion(type="text", options=" ", sequence_number=3, size="18", question="What is your expected Degree?")
s3 = SurveyQuestion(type="text", options=['MM-YYYY'], sequence_number=3, size="18", question="What is your expected Graduation Date?")
# view functions
def configure(request, experiment_id=None):
    experiment = Experiment.objects.get(pk=experiment_id)
    return render_to_response('sanitation/configure.html', {
        'experiment': experiment,
        },
        context_instance=RequestContext(request))

def consent(request, experiment):
	logger.debug("handling consent")
	consent = ['Introduction to Global Health Class', symbol,'one week', growth_rate]
	return render_to_response('sanitation/consent.html', locals(), context_instance=RequestContext(request))

def survey(request, experiment):
	logger.debug("handling survey")
	return render_to_response('sanitation/survey.html', globals(), context_instance=RequestContext(request))

def quiz(request, experiment):
	logger.debug("handling quiz")
	return render_to_response('sanitation/quiz.html', globals(), context_instance=RequestContext(request))

def instructions(request, experiment):
	logger.debug("handling instructions")
	return render_to_response('sanitation/instructions.html', globals(), context_instance=RequestContext(request))

def play(request, experiment):
	treatment = "In-group"
	logger.debug("handling play")
	return render_to_response('sanitation/play.html', globals(), context_instance=RequestContext(request))

def participate(request, experiment_id=None):
# lookup participant's current location and then invoke the method named by the location
    participant = request.user.participant
    experiment = Experiment.objects.get(pk=experiment_id)
# FIXME: this isn't implemented
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
