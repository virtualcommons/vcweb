from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.template import Context
from vcweb import settings
import logging

logger = logging.getLogger(__name__)

def send_email(subject='vcweb experiment notification', context=None, template_name=None, from_address='vcweb@asu.edu', recipients=None, reply_to=None):
    if recipients is None:
        logger.warning("ignoring attempt to send an email (%s) to no recipients from %s", template_name, reply_to)
        return
    text_content = render_to_string('email/%s.txt' % template_name, context)
    try:
        html_content = render_to_string('email/%s.html' % template_name, context)
    except:
        logger.debug("no html content found for template %s", template_name)
    headers = {}
    bcc = []
    if reply_to is not None:
        bcc.append(reply_to)
        headers['Reply-To'] = reply_to
    for recipient in recipients:
        message = EmailMultiAlternatives(subject, text_content, from_address, [recipient], bcc=bcc, headers=headers)
        if html_content is not None:
            message.attach_alternative(html_content, 'text/html')
        message.send()

def send_experiment_started(experiment, subject='a vcweb experiment you are participating in has just started', extra_instructions=''):
    send_email(context = Context({
        'experiment': experiment,
        'special_instructions': extra_instructions,
        'full_participant_url': 'https://%s%s' % (settings.SERVER_NAME, experiment.participant_url)
        }),
        subject=subject,
        template_name='experiment-started',
        reply_to=experiment.experimenter.email,
        recipients=experiment.participant_emails)


