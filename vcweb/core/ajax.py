from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader_tags import BlockNode, ExtendsNode
from django.template import loader, Context, RequestContext

from vcweb.core import dumps
from vcweb.core.decorators import experimenter_required, dajaxice_register
from vcweb.core.forms import BookmarkExperimentMetadataForm
from vcweb.core.http import JsonResponse
from vcweb.core.models import (Experiment, RoundData, ExperimentMetadata, BookmarkedExperimentMetadata,
        get_chat_message_parameter, )

import logging
logger = logging.getLogger(__name__)

def get_template(template):
    if isinstance(template, (tuple, list)):
        return loader.select_template(template)
    return loader.get_template(template)

class BlockNotFound(Exception):
    pass

def render_template_block(template, block, context):
    """
    Renders a single block from a template. This template should have previously been rendered.
    """
    return render_template_block_nodelist(template.nodelist, block, context)

def render_template_block_nodelist(nodelist, block, context):
    for node in nodelist:
        if isinstance(node, BlockNode) and node.name == block:
            return node.render(context)
        for key in ('nodelist', 'nodelist_true', 'nodelist_false'):
            if hasattr(node, key):
                try:
                    return render_template_block_nodelist(getattr(node, key), block, context)
                except:
                    pass
    for node in nodelist:
        if isinstance(node, ExtendsNode):
            try:
                return render_template_block(node.get_parent(context), block, context)
            except BlockNotFound:
                pass
    raise BlockNotFound

def render_block_to_string(template_name, block, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders the given block with the given dictionary as
    context. Returns a string.
    """
    dictionary = dictionary or {}
    t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    t.render(context_instance)
    return render_template_block(t, block, context_instance)

def direct_block_to_template(request, template, block, extra_context=None, mimetype=None, **kwargs):
    """
    Render a given block in a given template with any extra URL parameters in the context as
    ``{{ params }}``.
    """
    if extra_context is None:
        extra_context = {}
    dictionary = {'params': kwargs}
    for key, value in extra_context.items():
        if callable(value):
            dictionary[key] = value()
        else:
            dictionary[key] = value
    c = RequestContext(request, dictionary)
    t = get_template(template)
    t.render(c)
    return HttpResponse(render_template_block(t, block, c), mimetype=mimetype)

def _get_experiment(request, pk):
    experiment = get_object_or_404(Experiment.objects.select_related('experimenter'), pk=pk)
    if request.user.experimenter == experiment.experimenter:
        return experiment
    raise Experiment.DoesNotExist("Sorry, %s - you do not have access to experiment %s" % (experiment.experimenter, pk))

def _render_experiment_monitor_block(block, experiment, request):
    return render_block_to_string('experimenter/monitor.html', block, { 'experiment': experiment },
            context_instance=RequestContext(request))

@experimenter_required
@dajaxice_register
def bookmark_experiment_metadata(request):
    form = BookmarkExperimentMetadataForm(request.POST or None)
    try:
        if form.is_valid():
            experiment_metadata_id = form.cleaned_data.get('experiment_metadata_id')
            experimenter_id = form.cleaned_data.get('experimenter_id')
            experimenter = request.user.experimenter
            if experimenter.pk == experimenter_id:
                experiment_metadata = get_object_or_404(ExperimentMetadata, pk=experiment_metadata_id)
                bem = BookmarkedExperimentMetadata.objects.get_or_create(experimenter=experimenter,
                        experiment_metadata=experiment_metadata)
                return JsonResponse(dumps({'success': True}))
    except:
        logger.debug("invalid bookmark experiment metadata request: %s", request)

    return JsonResponse(dumps({'success': False}))

@experimenter_required
@dajaxice_register
def save_experimenter_notes(request, experiment_id, notes=None):
    experiment = _get_experiment(request, experiment_id)
    current_round_data = experiment.current_round_data
    current_experimenter_notes = current_round_data.experimenter_notes
    if notes != current_round_data.experimenter_notes:
        if current_experimenter_notes:
            experiment.log("Replacing existing experimenter notes %s with %s" % (current_experimenter_notes, notes))
        current_round_data.experimenter_notes = notes
        current_round_data.save()
        return JsonResponse(dumps({ 'success': True }))
    else:
        return JsonResponse(dumps({ 'success': False, 'message': "Experimenter notes were unchanged, no need to save '%s'" % notes}))


@experimenter_required
@dajaxice_register
def get_experiment_model(request, pk):
    return _get_experiment(request, pk).to_json()

@experimenter_required
@dajaxice_register
def get_round_data(request, pk):
    round_data = get_object_or_404(RoundData, pk=pk)
    group_data_values = [gdv.to_dict(cacheable=True) for gdv in round_data.group_data_value_set.select_related('group', 'parameter').all()]
    participant_data_values = [pdv.to_dict(include_email=True, cacheable=True) for pdv in round_data.participant_data_value_set.select_related('participant_group_relationship__participant__user', 'parameter').exclude(parameter=get_chat_message_parameter())]
    return dumps({
        'groupDataValues': group_data_values,
        'participantDataValues': participant_data_values
        })

@experimenter_required
@dajaxice_register
def experiment_controller(request, pk, action=None):
    experimenter = request.user.experimenter
    experiment = _get_experiment(request, pk)
    try:
        response_tuples = experiment.invoke(action, experimenter)
        logger.debug("invoking action %s results: %s", action, str(response_tuples))
        return experiment.to_json()
    except AttributeError as e:
        logger.warning("no attribute %s on experiment %s (%s)", action, experiment.status_line, e)
        return dumps({
            'success': False,
            'message': 'Invalid experiment action %s' % action
            })
