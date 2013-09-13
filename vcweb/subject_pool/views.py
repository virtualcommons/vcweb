from django.views.generic import View
from django.shortcuts import render_to_response, redirect, RequestContext
from vcweb.core.models import is_experimenter, Experiment
from vcweb.core.decorators import experimenter_required
from django.views.generic.list import ListView
from models import Session
from forms import SessionForm
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.core.urlresolvers import reverse

import logging

logger = logging.getLogger(__name__)

def index(request):

    if is_experimenter(request.user):
        #return render_to_response('forestry/experimenter-index.html')
        return redirect('subject-pool:experimenter_index')
    else:
        logger.warning("user %s isn't an experimenter or participant", request.user)
        return redirect('home')

@experimenter_required
def experimenter_index(request):
    experimenter = request.user.experimenter
    #experiments = experimenter.experiment_set.filter(experiment_metadata=get_experiment_metadata())
    return render_to_response('subject-pool/experimenter-index.html', locals(), context_instance=RequestContext(request))

class SessionMixin(object):
    model = Session
    def get_context_data(self, **kwargs):
        kwargs.update({'object_name':'Session'})
        return kwargs

class SessionFormMixin(SessionMixin):
    form_class = SessionForm
    template_name = 'session/object_form.html'

class SessionList(SessionMixin, ListView):
    template_name = 'subject-pool/object_list.html'


class ViewSession(SessionMixin, DetailView):
    pass

class NewSession(SessionFormMixin, CreateView):
    pass

class EditSession(SessionFormMixin, UpdateView):
    pass

class DeleteSession(SessionMixin, DeleteView):
    template_name = 'subject-pool/object_confirm_delete.html'
    def get_success_url(self):
        return reverse('session_list')

