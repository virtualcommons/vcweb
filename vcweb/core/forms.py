from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _
from bootstrap.forms import BootstrapForm, BootstrapMixin, Fieldset

from vcweb.core.models import (Experimenter, Institution)

from django.core.validators import email_re

import re

import logging

logger = logging.getLogger(__name__)

REQUIRED_EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class BaseRegistrationForm(BootstrapForm):
    first_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES), help_text=_('Please enter a valid email.  We will never share your email in any way, shape, or form.'))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES), help_text=_('The primary institution, if any, you are affiliated with.'))
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
    class Meta:
        layout = (
                Fieldset("", "first_name", "last_name", "email", "password", "confirm_password", "institution",'experimenter'),
                )

class VcwebPasswordResetForm(BootstrapMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        logger.debug("creating vcweb password reset form: %s %s", args, kwargs)
        super(VcwebPasswordResetForm, self).__init__(*args, **kwargs)

class LoginForm(BootstrapForm):
    class Meta:
        layout = (
                Fieldset("", 'email', 'password'),
                )
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        email = self.cleaned_data.get('email').lower()
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Your combination of email and password was incorrect."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This user has been deactivated. Please contact us if this is in error."))
        return self.cleaned_data

class ParticipantAccountForm(BaseRegistrationForm):
    pass

class ExperimenterAccountForm(BootstrapMixin, forms.ModelForm):
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
        for line in lines:
            # try to split by spaces first, expect first name last name email
            data = line.split()
            email = ''
            if len(data) == 1:
                email = data[0]
            elif len(data) == 3:
                (first_name, last_name, email) = data
                logger.debug("first name %s, last name %s, email %s", first_name, last_name, email)
            if not email_re.match(email):
                raise ValidationError(_(u'%s is not a valid email address.' % data))
        return lines

class RegisterParticipantsForm(BootstrapForm):
    experiment_pk = forms.IntegerField(widget=widgets.HiddenInput)
    experiment_passcode = forms.CharField(min_length=3, label="Experiment passcode", help_text=_('The password used to login to your experiment.'), initial='test')
    institution_name = forms.CharField(min_length=3, label="Institution name",
            required=False, initial='Arizona State University',
            help_text=_('The name of the institution to be associated with these test participants'))
    institution_url = forms.URLField(min_length=3, label='Institution URL',
            required=False, initial='http://www.asu.edu/',
            verify_exists=True, help_text=_('A URL, if applicable, for the institution (e.g., http://www.asu.edu)'))

    def clean(self):
        institution_name = self.cleaned_data.get('institution_name')
        institution_url = self.cleaned_data.get('institution_url')
        if institution_name is None and institution_url is None:
            self.institution = None
        else:
            logger.debug("get or create institution with name [%s] and url [%s]", institution_name, institution_url)
            (institution, created) = Institution.objects.get_or_create(name=institution_name, url=institution_url)
            self.institution = institution
        return self.cleaned_data


class RegisterSimpleParticipantsForm(RegisterParticipantsForm):
    email_suffix = forms.CharField(min_length=3, initial='asu.edu',
            help_text=_('An email suffix without the "@" symbol.  Generated participants will have usernames of the format s1..sn@email_suffix.  For example, if you register 20 participants with an email suffix of example.edu, the system will generate 20 participants with usernames ranging from s1@example.edu, s2@example.edu, s3@example.edu, ... s20@example.edu.'))
    number_of_participants = forms.IntegerField(min_value=1, help_text=_('The number of participants to register with this experiment.'))

class RegisterEmailListParticipantsForm(RegisterParticipantsForm):
    participant_emails = EmailListField(label="Participant emails", help_text=_('A newline delimited list of emails to register as participants for this experiment.'))

class RegisterExcelParticipantsForm(RegisterParticipantsForm):
    file = forms.FileField()

class ChatForm(forms.Form):
    message = forms.CharField(max_length=512)
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

