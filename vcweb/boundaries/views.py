from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template.context import RequestContext
from django.views.generic import View
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from vcweb.core.decorators import participant_required, experimenter_required
from vcweb.core.forms import QuizForm
from vcweb.core.models import is_participant, is_experimenter, Experiment
from vcweb.core.views import ParticipantSingleExperimentMixin
import logging

logger = logging.getLogger(__name__)

def participate(request):
    pass
