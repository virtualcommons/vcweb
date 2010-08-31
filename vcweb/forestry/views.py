# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect
from django.template.context import RequestContext
from vcweb.core.models import GameInstance
import logging

logger = logging.getLogger('forestry.views')

def index(request):
    return render_to_response('forestry/index.html', RequestContext(request))

def configure(request):
    return Http404()


def experimenter(request):
    return Http404()

@login_required
def participate(request, game_instance_id=None):
    if game_instance_id is None:
        logger.debug("No game instance id specified, redirecting to forestry index page.")
        return redirect('index')
    try:
        participant = request.user.participant
    except AttributeError:
        logger.debug("No participant available on logged in user %s" % request.user)
        return redirect('index')
    try:
        game_instance = GameInstance.objects.get(pk=game_instance_id)
        return render_to_response('forestry/participate.html',
                                  { 'participant': participant, 'game_instance' : game_instance },
                                  context_instance=RequestContext(request))
    except GameInstance.DoesNotExist:
        logger.warning("No game instance for id [%s]" % game_instance_id)
        return redirect('index')



