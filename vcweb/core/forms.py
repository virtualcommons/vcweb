import email
import logging
import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.forms import widgets, ValidationError, CheckboxInput
from django.utils.translation import ugettext_lazy as _
import autocomplete_light

from vcweb.core.autocomplete_light_registry import InstitutionAutocomplete, ParticipantMajorAutocomplete
from vcweb.core.models import (Experimenter, Institution, Participant, ExperimentMetadata, ExperimentConfiguration,
                               ExperimentParameterValue, RoundConfiguration, RoundParameterValue)


logger = logging.getLogger(__name__)

REQUIRED_EMAIL_ATTRIBUTES = {'class': 'required email'}
REQUIRED_ATTRIBUTES = {'class': 'required'}


class NumberInput(widgets.Input):
    input_type = 'number'


class RangeInput(widgets.Input):
    input_type = 'range'


class EmailInput(widgets.TextInput):
    input_type = 'email'


class URLInput(widgets.Input):
    input_type = 'url'


class BaseRegistrationForm(forms.Form):
    first_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=EmailInput(attrs=REQUIRED_EMAIL_ATTRIBUTES), help_text=_(
        'Please enter a valid email.  We will never share your email in any way, shape, or form.'))
    password = forms.CharField(
        widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(
        widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete), required=True,
                                  help_text=_('The primary institution, if any, you are affiliated with.'))

    def clean_email(self):
        email_address = self.cleaned_data['email'].lower()
        try:
            User.objects.get(email=email_address)
        except User.DoesNotExist:
            return email_address
        raise forms.ValidationError(_("This email address is already registered in our system."),
                                    code='already-registered')

    def clean(self):
        cleaned_data = super(BaseRegistrationForm, self).clean()
        pw = cleaned_data['password']
        confirm_pw = cleaned_data['confirm_password']
        if pw == confirm_pw:
            return cleaned_data
        raise forms.ValidationError(
            _("Please make sure your passwords match."), code='invalid')


class RegistrationForm(BaseRegistrationForm):
    experimenter = forms.BooleanField(required=False,
                                      help_text=_('Check this box if you would like to request experimenter access.'))


class VcwebPasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super(VcwebPasswordResetForm, self).__init__(*args, **kwargs)


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=EmailInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(
        widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        email_address = cleaned_data.get('email').lower()
        password = cleaned_data.get('password')
        if email_address and password:
            self.user_cache = authenticate(
                username=email_address, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    _("Your combination of email and password was incorrect."), code='invalid')
            elif not self.user_cache.is_active:
                raise forms.ValidationError(
                    _("This user has been deactivated. Please contact us if this is in error."))
        return cleaned_data


class AsuRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES),
                             help_text=_('We will never share your email.'))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(AsuRegistrationForm, self).__init__(*args, **kwargs)
        if instance is not None:
            self.fields.keyOrder = ['first_name', 'last_name', 'email', 'gender', 'class_status', 'major',
                                    'favorite_sport', 'favorite_food', 'favorite_color', 'favorite_movie_genre']
            for attr in ('first_name', 'last_name', 'email', 'major'):
                self.fields[attr].initial = getattr(instance, attr)

    class Meta:
        model = Participant
        fields = ['major', 'class_status', 'gender', 'favorite_sport', 'favorite_color', 'favorite_food',
                  'favorite_movie_genre']
        widgets = {
            'major': autocomplete_light.TextWidget(ParticipantMajorAutocomplete)
        }


class ParticipantAccountForm(forms.ModelForm):
    first_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES),
                             help_text=_('We will never share your email.'))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete), required=False,
                                  help_text=_('The primary institution, if any, you are affiliated with.'))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(ParticipantAccountForm, self).__init__(*args, **kwargs)
        if instance is not None:
            self.fields.keyOrder = ['first_name', 'last_name', 'email', 'institution', 'can_receive_invitations',
                                    'major', 'class_status', 'gender', 'favorite_sport', 'favorite_color',
                                    'favorite_food', 'favorite_movie_genre']
            self.fields['class_status'].label = 'Class Status'
            self.fields[
                'can_receive_invitations'].label = 'Receive invitations for experiments?'

            for attr in ('first_name', 'last_name', 'email'):
                self.fields[attr].initial = getattr(instance, attr)

            institution = instance.institution
            if institution:
                self.fields['institution'].initial = institution.name

    class Meta:
        model = Participant
        fields = ['major', 'class_status', 'gender', 'can_receive_invitations', 'favorite_sport', 'favorite_color',
                  'favorite_food', 'favorite_movie_genre']

        widgets = {
            'major': autocomplete_light.TextWidget(ParticipantMajorAutocomplete),
        }

    def clean(self):
        data = super(forms.ModelForm, self).clean()
        email_address = data.get('email')
        validate_email(email_address)
        # raise forms.ValidationError(_("This email address is already in our system."))

        can_be_invited = data.get('can_receive_invitations')
        major = data.get('major')
        gender = data.get('gender')
        class_status = data.get('class_status')
        favorite_food = data.get('favorite_food')
        favorite_color = data.get('favorite_color')
        favorite_sport = data.get('favorite_sport')
        favorite_movie_genre = data.get('favorite_movie_genre')
        if not email_address:
            raise forms.ValidationError(
                _("Please enter a valid email address"))

        if can_be_invited and (not major or not gender or not class_status or not favorite_food or not favorite_color
                               or not favorite_sport or not favorite_movie_genre):
            raise forms.ValidationError(_("Please enter your major, gender, class status, favorite food, favorite color"
                                          ", favorite sport and favorite movie genre to receive invitations"))

        return data


class ExperimenterAccountForm(forms.ModelForm):
    first_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(
        widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES),
                             help_text=_('We will never share your email.'))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete), required=False,
                                  help_text=_('The primary institution, if any, you are affiliated with.'))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance is not None:
            super(ExperimenterAccountForm, self).__init__(*args, **kwargs)
            self.fields.keyOrder = [
                'first_name', 'last_name', 'email', 'institution', ]

            for attr in ('first_name', 'last_name', 'email'):
                self.fields[attr].initial = getattr(instance, attr)

            institution = instance.institution
            if institution:
                self.fields['institution'].initial = institution.name
        else:
            super(ExperimenterAccountForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Experimenter
        exclude = ('approved', 'institution',
                   'failed_password_attempts', 'authentication_token', 'user')


email_separator_re = re.compile(r'[^\w\.\-\+@_]+')


class ExperimentConfigurationForm(forms.ModelForm):

    class Meta:
        model = ExperimentConfiguration
        exclude = ('creator', 'last_modified', 'date_created',
                   'cached_final_sequence_number', 'invitation_text')
        widgets = {
            'registration_email_subject': forms.Textarea(attrs={'class': 'form-control', 'cols': 40, 'rows': 2}),
        }


class ExperimentParameterValueForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ExperimentParameterValueForm, self).__init__(*args, **kwargs)
        self.fields['parameter'].queryset = self.fields[
            'parameter'].queryset.filter(scope='experiment')

        for name, field in self.fields.items():
            if field.widget.__class__ == CheckboxInput:
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

    class Meta:
        model = ExperimentParameterValue
        exclude = ('experiment_configuration', 'last_modified', 'date_created')
        widgets = {
            'string_value': forms.Textarea(attrs={'cols': 40, 'rows': 3}),
        }


class RoundConfigurationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RoundConfigurationForm, self).__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.widget.__class__ == CheckboxInput:
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

            help_text = field.help_text
            field.help_text = None
            if help_text != '':
                field.widget.attrs.update(
                    {'class': 'has-popover', 'data-content': help_text, 'data-placement': 'right',
                     'data-container': 'div.modal-dialog'})

    class Meta:
        model = RoundConfiguration
        exclude = ('experiment_configuration', 'last_modified', 'date_created', 'template_filename', 'instructions',
                   'debriefing', 'group_cluster_size')


class RoundParameterValueForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RoundParameterValueForm, self).__init__(*args, **kwargs)
        self.fields['parameter'].queryset = self.fields[
            'parameter'].queryset.filter(scope='round')

        for name, field in self.fields.items():
            if field.widget.__class__ == CheckboxInput:
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

    class Meta:
        model = RoundParameterValue
        exclude = ('round_configuration', 'last_modified', 'date_created')
        widgets = {
            'string_value': forms.Textarea(attrs={'cols': 40, 'rows': 3}),
        }


class EmailListField(forms.CharField):
    widget = forms.Textarea

    def clean(self, value):
        super(EmailListField, self).clean(value)
        lines = value.split('\n')
        #emails = email_separator_re.split(value)
        if not lines:
            raise ValidationError(
                _(u'You must enter at least one email address.'))
        emails = []
        for line in lines:
            # check for emails in the form of Allen T Lee <allen.t.lee@asu.edu>
            (full_name, email_address) = email.utils.parseaddr(line)
            logger.debug("full name %s, email %s", full_name, email_address)
            email_address = email_address.strip()
            if not email_address:
                logger.debug("blank line, ignoring")
                continue
            # FIXME: the only way to really test a valid email address is to try to send an email to it but keeping it
            # simple for the time being.
            validate_email(email_address)
            emails.append(line)
        return emails


class RegisterParticipantsForm(forms.Form):
    experiment_pk = forms.IntegerField(widget=widgets.HiddenInput)
    start_date = forms.DateField(required=False,
                                 help_text=_('''Date this experiment should activate and start.
                                 Used for multi-day experiments with daily rounds'''))
    experiment_password = forms.CharField(required=False, min_length=3,
                                          help_text=_('''Participant password to login to the experiment.
                                           If blank, a unique password will be autogenerated by the system for each participant.'''))
    institution_name = forms.CharField(min_length=3, label="Institution name",
                                       required=False, initial='Arizona State University',
                                       widget=autocomplete_light.TextWidget(
                                           InstitutionAutocomplete),
                                       help_text=_('Institution to associate with these participants if they do not already exist in the system.'))
    registration_email_from_address = forms.EmailField(widget=EmailInput(), label=_('Sender email'),
                                                       help_text=_(
                                                           "Email address to use in the from field of the registration email"))
    sender = forms.CharField(required=False, label='Sender name', help_text=_(
        'Name to use when signing off the registration email'), initial="The vcweb development team")
    registration_email_subject = forms.CharField(min_length=3, label="Email subject",
                                                 help_text=_('Subject line for the registration email'))
    registration_email_text = forms.CharField(required=False, widget=forms.Textarea, label="Email body",
                                              help_text=_('Custom registration email text to appear at the beginning of the message, before the generated registration text.'))

    def clean_institution(self):
        institution_name = self.cleaned_data.get('institution_name').strip()
        if institution_name is None:
            self.institution = None
        else:
            (institution, created) = Institution.objects.get_or_create(
                name=institution_name)
            logger.debug(
                "get or create institution %s - created? %s", institution_name, created)
            self.institution = institution
        return self.institution


class RegisterTestParticipantsForm(RegisterParticipantsForm):
    username_suffix = forms.CharField(min_length=1, initial='asu',
                                      help_text=_(
                                          '''Appended to every generated username before the "@" symbol, e.g., s1asu@mailinator.com'''))
    email_suffix = forms.CharField(min_length=3, initial='mailinator.com',
                                   help_text=_('''An email suffix without the "@" symbol.  Generated participants will
                                    receive usernames of s1<username_suffix>@<email_suffix>..sn<username_suffix>@<email_suffix>.
                                    For example, if you register 20 participants with a username suffix of asu and an
                                    email suffix of mailinator.com, the system will generate 20 participants with
                                    usernames ranging from s1asu@mailinator.com, s2asu@mailinator.com,
                                    s3asu@mailinator.com, ... s20asu@mailinator.com.'''))
    number_of_participants = forms.IntegerField(
        min_value=2, initial=10, widget=NumberInput(attrs={'min': 2}))


class RegisterEmailListParticipantsForm(RegisterParticipantsForm):
    participant_emails = EmailListField(label="Participant emails",
                                        help_text=_(
                                            'A newline delimited list of participant emails to register for this experiment.'))


class RegisterExcelParticipantsForm(RegisterParticipantsForm):
    file = forms.FileField()


class ChatForm(forms.Form):
    message = forms.CharField()
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    target_participant_group_id = forms.IntegerField(
        widget=forms.HiddenInput, required=False)

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
            self.cleaned_data['experiment_metadata'] = ExperimentMetadata.objects.get(
                pk=experiment_metadata_id)
        except ExperimentMetadata.DoesNotExist:
            raise ValidationError(
                "Invalid experiment metadata id: %s" % experiment_metadata_id)
        return experiment_metadata_id

    def clean_experimenter_id(self):
        experimenter_id = self.cleaned_data['experimenter_id']
        try:
            self.cleaned_data['experimenter'] = Experimenter.objects.get(
                pk=experimenter_id)
        except Experimenter.DoesNotExist:
            raise ValidationError(
                "Invalid experimenter id %s" % experimenter_id)
        return experimenter_id


class UpdateExperimentForm(forms.Form):
    action = forms.CharField(max_length=64)
    experiment_id = forms.IntegerField(widget=forms.HiddenInput)


class LikeForm(forms.Form):
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)


class CommentForm(forms.Form):
    message = forms.CharField(max_length=512)
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)


class LogMessageForm(forms.Form):
    log_levels = [(getattr(logging, levelName), levelName) for levelName in
                  ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')]
    level = forms.ChoiceField(choices=log_levels)
    message = forms.CharField()

    def clean_level(self):
        level = int(self.cleaned_data['level'])
        if level in dict(self.log_levels):
            return level
        raise ValidationError(_("invalid log level %s" % level))


class SingleIntegerDecisionForm(forms.Form):
    integer_decision = forms.IntegerField(required=True, min_value=0)
    participant_group_id = forms.IntegerField(
        required=True, widget=forms.widgets.HiddenInput)
    submitted = forms.BooleanField(
        required=False, widget=forms.widgets.HiddenInput)


class QuizForm(forms.Form):
    name_question = forms.CharField(
        max_length=64, label=_("What is your name?"))

    def __init__(self, *args, **kwargs):
        quiz_questions = []
        try:
            quiz_questions = kwargs.pop('quiz_questions')
        finally:
            super(QuizForm, self).__init__(*args, **kwargs)
            for quiz_question in quiz_questions:
                self.fields['quiz_question_%d' % quiz_question.pk] = forms.CharField(
                    label=quiz_question.label)

    def extra_questions(self):
        for name, value in self.cleaned_data.items():
            if name.startswith('quiz_question_'):
                yield (self.fields[name].label, value)
