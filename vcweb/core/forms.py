from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.core.validators import email_re
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _

from bootstrap_toolkit.widgets import BootstrapDateInput
from vcweb.core.autocomplete_light_registry import InstitutionAutocomplete
from vcweb.core.models import (Experimenter, Institution, Participant, ExperimentMetadata)

import autocomplete_light
import logging
import re

logger = logging.getLogger(__name__)

REQUIRED_EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class NumberInput(widgets.Input):
    input_type = 'number'

class RangeInput(widgets.Input):
    input_type = 'range'

class EmailInput(widgets.TextInput):
    input_type = 'email'

class URLInput(widgets.Input):
    input_type = 'url'

class BaseRegistrationForm(forms.Form):
    first_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=EmailInput(attrs=REQUIRED_EMAIL_ATTRIBUTES), help_text=_('Please enter a valid email.  We will never share your email in any way, shape, or form.'))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete),required=True, help_text=_('The primary institution, if any, you are affiliated with.'))
    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_("This email address is already in our system."))

    def clean_confirm_password(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password == confirm_password:
            return confirm_password
        raise forms.ValidationError(_("Please make sure your passwords match."))

class RegistrationForm(BaseRegistrationForm):
    experimenter = forms.BooleanField(required=False, help_text=_('Check this box if you would like to request experimenter access.'))

class VcwebPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super(VcwebPasswordResetForm, self).__init__(*args, **kwargs)

class LoginForm(forms.Form):
    email = forms.EmailField(widget=EmailInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        email = self.cleaned_data['email'].lower()
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Your combination of email and password was incorrect."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This user has been deactivated. Please contact us if this is in error."))
        return self.cleaned_data


class ParticipantAccountForm(forms.ModelForm):
    pk = forms.IntegerField(widget=widgets.HiddenInput())
    first_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES), help_text=_('Please enter a valid email.  We will never share your email in any way, shape, or form.'))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete), required=False, help_text=_('The primary institution, if any, you are affiliated with.'))
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is not None:
            super(ParticipantAccountForm, self).__init__(*args, **kwargs)
            self.fields.keyOrder = ['pk', 'first_name', 'last_name', 'email', 'institution', 'can_receive_invitations', 'major', 'class_status', 'gender']
            self.fields['class_status'].label = 'Class Status'
            for attr in ("pk", "first_name", 'last_name', 'email'):
                self.fields[attr].initial = getattr(instance, attr)

            institution = instance.institution
            if institution:
                self.fields['institution'].initial = institution.name
        else:
            super(ParticipantAccountForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Participant
        fields = ['major', 'class_status', 'gender', 'can_receive_invitations']
        """
        widgets = {
            'major': autocomplete_light.TextWidget('MajorAutocomplete'),
        }
        """


    def clean(self):
        data = super(forms.ModelForm, self).clean()
        m = data.get('email')
        if not email_re.match(m):
                raise ValidationError(_(u'%s is not a valid email address.' % data))
        # raise forms.ValidationError(_("This email address is already in our system."))

        can_be_invited = data.get('can_receive_invitations')
        major = data.get('major')
        gender = data.get('gender')
        class_status = data.get('class_status')
        if not m:
            raise forms.ValidationError(_("You have forgotten your Email address"))

        if can_be_invited:
            if not major or not gender or not class_status:
                raise forms.ValidationError(_("You need to enter your major, gender and class status if you wan't to receive Invitations"))

        return data

class ExperimenterAccountForm(forms.ModelForm):
    class Meta:
        model = Experimenter
        exclude = ('user',)

email_separator_re = re.compile(r'[^\w\.\-\+@_]+')
class EmailListField(forms.CharField):
    widget = forms.Textarea
    def clean(self, value):
        super(EmailListField, self).clean(value)
        lines = value.split('\n')
        #emails = email_separator_re.split(value)
        if not lines:
            raise ValidationError(_(u'You must enter at least one email address.'))
        emails = []
        for line in lines:
            # try to split by spaces first, expect first name last name email
            data = line.split()
            email = ''
            if len(data) == 1:
                email = data[0]
            elif len(data) == 3:
                (first_name, last_name, email) = data
                logger.debug("first name %s, last name %s, email %s", first_name, last_name, email)
            email = email.strip()
            if not email:
                logger.debug("blank line, ignoring")
                continue
            # FIXME: the only way to really test a valid email address is to try to send an email to it but keeping it
            # simple for the time being.
            if not email_re.match(email):
                raise ValidationError(_(u'%s is not a valid email address.' % data))
            emails.append(line)
        return emails

class RegisterParticipantsForm(forms.Form):
    experiment_pk = forms.IntegerField(widget=widgets.HiddenInput)
    start_date = forms.DateField(required=False, widget=BootstrapDateInput(), help_text=_('The date this experiment will start, used for multi-day experiments with daily rounds'))
    experiment_password = forms.CharField(required=False, min_length=3, help_text=_('Participants will login to the experiment using this password'), initial='test')
    institution = forms.CharField(min_length=3, label="Institution name",
            required=False, initial='Arizona State University',
            widget=autocomplete_light.TextWidget(InstitutionAutocomplete),
            help_text=_('Institution to associate with these participants'))
    registration_email_subject = forms.CharField(min_length=3, label="Email subject", help_text=_('Subject line for registration email'), initial='VCWEB experiment registration')
    registration_email_text = forms.CharField(required=False, widget=forms.Textarea, label="Email body")
    sender = forms.CharField(required=False, initial="The vcweb Development Team")

    def clean_institution(self):
        institution_name = self.cleaned_data.get('institution').strip()
        if institution_name is None:
            self.institution = None
        else:
            logger.debug("get or create institution %s", institution_name)
            (institution, created) = Institution.objects.get_or_create(name=institution_name)
            self.institution = institution
        return self.institution


class RegisterTestParticipantsForm(RegisterParticipantsForm):
    username_suffix = forms.CharField(min_length=1, initial='asu',
            help_text=_('''Appended to every generated username before the "@" symbol, e.g., s1asu@foo.com'''))
    email_suffix = forms.CharField(min_length=3, initial='mailinator.com',
            help_text=_('''
            An email suffix without the "@" symbol.  Generated participants will have usernames of the format
            s1<username_suffix>@<email_suffix>..sn<username_suffix>@<email_suffix>.  For example, if you register 20
            participants with a username suffix of asu and an email suffix of mailinator.com, the system will generate
            20 participants with usernames ranging from s1asu@mailinator.com, s2asu@mailinator.com,
            s3asu@mailinator.com, ... s20asu@mailinator.com.
            '''))
    number_of_participants = forms.IntegerField(min_value=2, initial=10, widget=NumberInput(attrs={'min': 2}))

class RegisterEmailListParticipantsForm(RegisterParticipantsForm):
    participant_emails = EmailListField(label="Participant emails", help_text=_('A newline delimited list of emails to register as participants for this experiment.'))

class RegisterExcelParticipantsForm(RegisterParticipantsForm):
    file = forms.FileField()

class ChatForm(forms.Form):
    message = forms.CharField()
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    target_participant_group_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    def clean_message(self):
        return self.cleaned_data['message']

class ParticipantGroupIdForm(forms.Form):
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)

class GeoCheckinForm(forms.Form):
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    latitude = forms.DecimalField(max_digits=8, decimal_places=5)
    longitude = forms.DecimalField(max_digits=8, decimal_places=5)
    accuracy = forms.FloatField(required=False)
    altitude = forms.FloatField(required=False)
    altitudeAccuracy = forms.FloatField(required=False)
    heading = forms.FloatField(required=False)
    speed = forms.FloatField(required=False)

class BookmarkExperimentMetadataForm(forms.Form):
    experiment_metadata_id = forms.IntegerField()
    experimenter_id = forms.IntegerField()

    def clean_experiment_metadata_id(self):
        experiment_metadata_id = self.cleaned_data['experiment_metadata_id']
        try:
            self.cleaned_data['experiment_metadata'] = ExperimentMetadata.objects.get(pk=experiment_metadata_id)
        except ExperimentMetadata.DoesNotExist:
            raise ValidationError("Invalid experiment metadata id: %s" % experiment_metadata_id)
        return experiment_metadata_id

    def clean_experimenter_id(self):
        experimenter_id = self.cleaned_data['experimenter_id']
        try:
            self.cleaned_data['experimenter'] = Experimenter.objects.get(pk=experimenter_id)
        except Experimenter.DoesNotExist:
            raise ValidationError("Invalid experimenter id %s" % experimenter_id)
        return experimenter_id


class ExperimentActionForm(forms.Form):
    action = forms.CharField(max_length=64)
    experiment_id = forms.IntegerField(widget=forms.HiddenInput)
    experimenter_id = forms.IntegerField(widget=forms.HiddenInput)

class LikeForm(forms.Form):
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)

class CommentForm(forms.Form):
    message = forms.CharField(max_length=512)
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)

class LogMessageForm(forms.Form):
    log_levels = [(getattr(logging, levelName), levelName) for levelName in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')]
    level = forms.ChoiceField(choices=log_levels)
    message = forms.CharField()

    def clean_level(self):
        level = int(self.cleaned_data['level'])
        if level in dict(self.log_levels):
            return level
        raise ValidationError(_("invalid log level %s" % level))

class SingleIntegerDecisionForm(forms.Form):
    integer_decision = forms.IntegerField(required=True, min_value=0)
    participant_group_id = forms.IntegerField(required=True, widget=forms.widgets.HiddenInput)
    submitted = forms.BooleanField(required=False, widget=forms.widgets.HiddenInput)

class QuizForm(forms.Form):
    name_question = forms.CharField(max_length=64, label=_("What is your name?"))
    def __init__(self, *args, **kwargs):
        quiz_questions = []
        try:
            quiz_questions = kwargs.pop('quiz_questions')
        finally:
            super(QuizForm, self).__init__(*args, **kwargs)
            for quiz_question in quiz_questions:
                self.fields['quiz_question_%d' % quiz_question.pk] = forms.CharField(label=quiz_question.label)

    def extra_questions(self):
        for name, value in self.cleaned_data.items():
            if name.startswith('quiz_question_'):
                yield (self.fields[name].label, value)

