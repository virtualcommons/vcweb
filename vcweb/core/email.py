from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import Context
import logging

logger = logging.getLogger(__name__)

def notify(subject='vcweb experiment notification', context=None, template_name=None, from_address='vcweb@asu.edu', to=['vcweb@asu.edu'], reply_to=None, bcc=None):
    text_content = render_to_string('email/%s.txt' % template_name, context)
    headers = {}
    if reply_to is not None:
        to.append(reply_to)
        headers['Reply-To'] = reply_to
    message = EmailMultiAlternatives(subject, text_content, from_address, to, bcc=bcc, headers=headers)
    try:
        html_content = render_to_string('email/%s.html' % template_name, context)
        message.attach_alternative(html_content, 'text/html')
    except:
        logger.debug("no html content found for template %s", template_name)
    message.send()

def send_experiment_started(experiment):
    notify(subject='a vcweb experiment you are participating in has just started',
            context = Context({'experiment': experiment}),
            template_name='experiment-started',
            reply_to=experiment.experimenter.email,
            bcc=experiment.participant_emails)


