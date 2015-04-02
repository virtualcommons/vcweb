from django.contrib.sites.models import Site, RequestSite
from django.template import Context
from django.template.loader import get_template
from vcweb.core.models import ExperimentSession

class InvitationEmail(object):

    def __init__(self, request):
        self.request = request
        self.plaintext_template = get_template('subjectpool/email/invitation-email.txt')

    @property
    def site_url(self):
        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(self.request)

        if self.request.is_secure():
            return "https://" + site.domain
        else:
            return "http://" + site.domain

    def get_plaintext_content(self, message, session_ids):
        context = Context({
            'SITE_URL': self.site_url,
            'invitation_text': message,
            'session_list': ExperimentSession.objects.filter(pk__in=session_ids),
        })
        return self.plaintext_template.render(context)
