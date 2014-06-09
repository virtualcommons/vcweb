import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader_tags import BlockNode, ExtendsNode
from django.template import loader, Context, RequestContext

from . import dumps
from .decorators import experimenter_required
from .http import JsonResponse
from .models import (
    Experiment, RoundData, get_chat_message_parameter, ExperimentConfiguration)

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
    experiment = get_object_or_404(
        Experiment.objects.select_related('experimenter'), pk=pk)
    if request.user.experimenter == experiment.experimenter:
        return experiment
    raise Experiment.DoesNotExist(
        "Sorry, %s - you do not have access to experiment %s" % (experiment.experimenter, pk))


def _render_experiment_monitor_block(block, experiment, request):
    return render_block_to_string('experimenter/monitor.html', block, {'experiment': experiment},
                                  context_instance=RequestContext(request))


@experimenter_required
def archive(request):
    experiment_id = request.POST.get('experiment_id')
    experiment = _get_experiment(request, experiment_id)
    experiment.complete()
    return JsonResponse(dumps({'success': True, 'experiment': experiment.to_dict(attrs=('monitor_url', 'status_line', 'controller_url'))}))


@experimenter_required
def clear_participants(request):
    experiment_id = request.POST.get('experiment_id')
    experiment = _get_experiment(request, experiment_id)
    experiment.clear_participants()
    return JsonResponse(dumps({'success': True, 'experiment': experiment.to_dict(attrs=('monitor_url', 'status_line', 'controller_url'))}))


@experimenter_required
def clone_experiment(request):
    experiment_id = request.POST.get('experiment_id')
    logger.debug("cloning experiment %s", experiment_id)
    experiment = get_object_or_404(Experiment, pk=experiment_id)
    experimenter = request.user.experimenter
    cloned_experiment = experiment.clone(experimenter=experimenter)
    return JsonResponse(dumps({'success': True, 'experiment': cloned_experiment.to_dict(attrs=('monitor_url', 'status_line', 'controller_url'))}))


@experimenter_required
def create_experiment(request):
    experiment_configuration_id = request.POST.get(
        'experiment_configuration_id')
    experiment_configuration = get_object_or_404(ExperimentConfiguration.objects.select_related(
        'experiment_metadata'), pk=experiment_configuration_id)
    experimenter = request.user.experimenter
    authentication_code = 'test'
    e = Experiment.objects.create(experimenter=experimenter,
                                  authentication_code=authentication_code,
                                  experiment_metadata=experiment_configuration.experiment_metadata,
                                  experiment_configuration=experiment_configuration,
                                  status=Experiment.Status.INACTIVE
                                  )
    return JsonResponse(dumps({'success': True, 'experiment': e.to_dict(attrs=('monitor_url', 'status_line', 'controller_url',))}))


@experimenter_required
def save_experimenter_notes(request):
    experiment_id = request.POST.get('experiment_id')
    notes = request.POST.get('notes')
    experiment = _get_experiment(request, experiment_id)
    current_round_data = experiment.current_round_data
    current_experimenter_notes = current_round_data.experimenter_notes
    if notes != current_round_data.experimenter_notes:
        if current_experimenter_notes:
            experiment.log("Replacing existing experimenter notes %s with %s" % (
                current_experimenter_notes, notes))
        current_round_data.experimenter_notes = notes
        current_round_data.save()
        return JsonResponse(dumps({'success': True}))
    else:
        return JsonResponse(dumps({'success': False, 'message': "Experimenter notes were unchanged, no need to save '%s'" % notes}))


@experimenter_required
def get_experiment_model(request, pk):
    return _get_experiment(request, pk).to_json()


@experimenter_required
def get_round_data(request):
    # FIXME: naively implemented performance wise, revisit if this turns into
    # a hot spot..
    pk = request.GET.get('pk')
    round_data = get_object_or_404(RoundData, pk=pk)
    group_data_values = [gdv.to_dict(
        cacheable=True) for gdv in round_data.group_data_value_set.select_related('group', 'parameter').all()]
    participant_data_values = [pdv.to_dict(include_email=True, cacheable=True) for pdv in round_data.participant_data_value_set.select_related(
        'participant_group_relationship__participant__user', 'parameter').exclude(parameter=get_chat_message_parameter())]
    return JsonResponse(dumps({
        'groupDataValues': group_data_values,
        'participantDataValues': participant_data_values
    }))


@experimenter_required
def experiment_controller(request):
    pk = request.POST.get('pk')
    action = request.POST.get('action')
    experimenter = request.user.experimenter
    experiment = _get_experiment(request, pk)
    logger.debug(
        "experimenter %s invoking %s on %s", experimenter, action, experiment)
    try:
        response_tuples = experiment.invoke(action, experimenter)
        logger.debug("invoking action %s: %s", action, str(response_tuples))
        return JsonResponse(dumps({
            'success': True,
            'experiment': experiment.to_dict()
        }))
    except AttributeError as e:
        logger.warning(
            "no attribute %s on experiment %s (%s)", action, experiment.status_line, e)
        return JsonResponse(dumps({
            'success': False,
            'message': 'Invalid experiment action %s' % action
        }))
