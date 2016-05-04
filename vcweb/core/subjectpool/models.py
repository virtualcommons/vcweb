from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import get_template
from django.utils import timezone
from vcweb.core.models import ExperimentSession, ParticipantSignup

class InvitationEmail(object):

    def __init__(self, request):
        self.request = request
        self.plaintext_template = get_template('subjectpool/email/invitation-email.txt')

    @property
    def site_url(self):
        site = get_current_site(self.request)
        if self.request.is_secure():
            return "https://" + site.domain
        else:
            return "http://" + site.domain

    def get_plaintext_content(self, message, session_ids):
        return self.plaintext_template.render({
            'SITE_URL': self.site_url,
            'invitation_text': message,
            'session_list': ExperimentSession.objects.filter(pk__in=session_ids),
        })


def generate_participant_report(writer=None, experiment_metadata=None, **kwargs):
    if writer is None or experiment_metadata is None:
        raise ValueError("Please enter in a valid writable thing and an experiment metadata")
    writer.writerow(["Participant List for {0}".format(experiment_metadata.title), experiment_metadata.namespace,
                     "Generated on {0}".format(timezone.now())])
    writer.writerow(['Email', 'Name', 'Username', 'Class Status', 'Attendance', 'Experiment Session Location',
                     'Experiment Session Start Time', 'Experiment Session End Time', 'Experiment Session Capacity',
                     'Experiment Session Creator', ])
    for ps in ParticipantSignup.objects.with_experiment_metadata(experiment_metadata=experiment_metadata, **kwargs):
        invitation = ps.invitation
        participant = invitation.participant
        experiment_session = invitation.experiment_session
        writer.writerow([participant.email, participant.full_name, participant.username, participant.class_status,
                         ps.get_attendance_display(),
                         experiment_session.location,
                         experiment_session.scheduled_date,
                         experiment_session.scheduled_end_date,
                         experiment_session.capacity,
                         experiment_session.creator
                         ])
