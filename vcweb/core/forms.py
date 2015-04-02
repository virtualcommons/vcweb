import email
import logging
import re
import autocomplete_light
import time

from hashlib import sha1

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm
from django.core.validators import validate_email
from django.forms import widgets, ValidationError, CheckboxInput
from django.forms.util import ErrorDict
from django.utils.translation import ugettext_lazy as _

from .autocomplete_light_registry import InstitutionAutocomplete, ParticipantMajorAutocomplete
from .models import (User, CommonsUser, Experimenter, Institution, Participant, ExperimentMetadata, ExperimentConfiguration,
                     ExperimentParameterValue, RoundConfiguration, RoundParameterValue)

from contact_form.forms import ContactForm

logger = logging.getLogger(__name__)

email_separator_re = re.compile(r'[^\w\.\-\+@_]+')


class NumberInput(widgets.Input):
    input_type = 'number'


class RangeInput(widgets.Input):
    input_type = 'range'


class EmailInput(widgets.TextInput):
    input_type = 'email'


class URLInput(widgets.Input):
    input_type = 'url'


"""
XXX: open registration currently disabled.

class BaseRegistrationForm(forms.Form):
    required_css_class = 'required'

    first_name = forms.CharField(widget=widgets.TextInput)
    last_name = forms.CharField(widget=widgets.TextInput)
    email = forms.EmailField(widget=EmailInput, help_text=_('Please enter a valid email.'))
    password = forms.CharField(widget=widgets.PasswordInput)
    confirm_password = forms.CharField(widget=widgets.PasswordInput)
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete),
                                  help_text=_('The primary institution, if any, you are affiliated with.'))

    def clean_email(self):
        email_address = self.cleaned_data.get('email', '').lower()
        if not email_address:
            raise ValidationError(_("Please enter a valid email address."))
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
        raise forms.ValidationError(_("Please make sure your passwords match."), code='invalid')

class RegistrationForm(BaseRegistrationForm):
    experimenter = forms.BooleanField(required=False,
                                      help_text=_('Check this box if you would like to request experimenter access.'))
"""


class VcwebPasswordResetForm(PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super(VcwebPasswordResetForm, self).__init__(*args, **kwargs)


class LoginForm(forms.Form):
    email = forms.EmailField(widget=EmailInput)
    password = forms.CharField(widget=widgets.PasswordInput)
    INVALID_AUTHENTICATION_MESSAGE = "Your combination of email and password was incorrect."
    INACTIVE_USER_AUTHENTICATION_MESSAGE = "This user has been deactivated. Please contact us if this is in error."

    def clean(self):
        cleaned_data = super(LoginForm, self).clean()
        email_address = cleaned_data.get('email')
        if email_address:
            email_address = email_address.lower()
        password = cleaned_data.get('password')
        if email_address and password:
            self.user_cache = authenticate(username=email_address, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_(LoginForm.INVALID_AUTHENTICATION_MESSAGE), code='invalid')
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_(LoginForm.INACTIVE_USER_AUTHENTICATION_MESSAGE))
        return cleaned_data


class AsuRegistrationForm(forms.ModelForm):
    required_css_class = 'required'

    first_name = forms.CharField(widget=widgets.TextInput)
    last_name = forms.CharField(widget=widgets.TextInput)
    email = forms.EmailField(widget=widgets.TextInput, help_text=_('''When experiments are scheduled you may receive an
    invitation to participate. Please be sure to enter a valid email address. We will never share your email.'''))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(AsuRegistrationForm, self).__init__(*args, **kwargs)
        if instance is not None:
            for attr in ('first_name', 'last_name', 'email', 'major'):
                self.fields[attr].initial = getattr(instance, attr)

    class Meta:
        model = Participant
        fields = ['first_name', 'last_name', 'email', 'gender', 'class_status', 'major', 'favorite_sport',
                  'favorite_food', 'favorite_color', 'favorite_movie_genre']
        widgets = {
            'major': autocomplete_light.TextWidget(ParticipantMajorAutocomplete)
        }

    def save(self, commit=True):
        profile = super(AsuRegistrationForm, self).save(commit=False)
        profile.can_receive_invitations = True
        profile.institution = Institution.objects.get(name="Arizona State University")
        user = profile.user
        user.email = self.cleaned_data.get('email').lower()
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        if commit:
            user.save()
            profile.save()


class AccountForm(forms.ModelForm):
    required_css_class = 'required'

    first_name = forms.CharField(widget=widgets.TextInput)
    last_name = forms.CharField(widget=widgets.TextInput)
    email = forms.EmailField(widget=widgets.TextInput, help_text=_('We will never share your email.'))
    institution = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete), required=False,
                                  help_text=_('The primary institution, if any, you are affiliated with.'))

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super(AccountForm, self).__init__(*args, **kwargs)
        if instance is not None:
            for attr in ('first_name', 'last_name', 'email', 'institution'):
                self.fields[attr].initial = getattr(instance, attr)

    def clean(self):
        data = super(AccountForm, self).clean()
        email_address = data.get('email')
        validate_email(email_address)

        if not email_address:
            raise forms.ValidationError(
                _("Please enter a valid email address"))

        if self.instance.email != email_address:
            if User.objects.filter(email=email_address).exists():
                raise forms.ValidationError(_("This email is already registered with our system, please try another.'"))
        return data

    def save(self, commit=True):
        profile = super(AccountForm, self).save(commit=False)
        institution_name = self.cleaned_data.get('institution')
        if institution_name:
            institution, created = Institution.objects.get_or_create(name=institution_name)
            profile.institution = institution
        else:
            profile.institution = None
            logger.debug('Institution is empty')

        for attr in ('first_name', 'last_name', 'email'):
            setattr(profile.user, attr, self.cleaned_data.get(attr))

        if commit:
            profile.save()
            profile.user.save()
        return profile


class ParticipantAccountForm(AccountForm):

    class Meta:
        model = Participant
        fields = ['gender', 'can_receive_invitations', 'class_status',
                  'major', 'favorite_sport', 'favorite_food', 'favorite_color', 'favorite_movie_genre']
        labels = {
            'can_receive_invitations': _('Receive invitations for experiments?')
        }
        widgets = {
            'major': autocomplete_light.TextWidget(ParticipantMajorAutocomplete),
        }

    def clean(self):
        data = super(ParticipantAccountForm, self).clean()

        email_address = data.get('email')
        can_receive_invitations = data.get('can_receive_invitations')
        major = data.get('major')
        gender = data.get('gender')
        class_status = data.get('class_status')
        favorite_food = data.get('favorite_food')
        favorite_color = data.get('favorite_color')
        favorite_sport = data.get('favorite_sport')
        favorite_movie_genre = data.get('favorite_movie_genre')

        if can_receive_invitations and not all([major, gender, class_status, favorite_food, favorite_color,
                                                favorite_sport, favorite_movie_genre]):
            raise forms.ValidationError(_("Please fill in all fields to be eligible for experiment invitations."))
        return data


class ExperimenterAccountForm(AccountForm):

    class Meta:
        model = Experimenter
        fields = ['first_name', 'last_name', 'email']


class ExperimentConfigurationForm(forms.ModelForm):
    required_css_class = 'required'

    def __init__(self, post_dict=None, instance=None, pk=None, **kwargs):
        if instance is None and pk is not None and pk != '-1':
            instance = ExperimentConfiguration.objects.get(pk=pk)
        super(ExperimentConfigurationForm, self).__init__(post_dict, instance=instance, **kwargs)

        if post_dict:
            self.request_type = post_dict.get('request_type')

        for name, field in self.fields.items():
            help_text = field.help_text
            field.help_text = None
            if help_text != '':
                field.widget.attrs.update(
                    {'class': 'has-popover', 'data-content': help_text, 'data-placement': 'right',
                     'data-container': 'body'})

    def save(self, commit=True):
        ec = super(ExperimentConfigurationForm, self).save(commit=False)
        if self.request_type == 'delete':
            logger.warn("Deleting experiment configuration %s", ec)
            ec.delete()
        elif commit:
            ec.save()
        return ec

    class Meta:
        model = ExperimentConfiguration
        exclude = ('creator', 'last_modified', 'date_created',
                   'cached_final_sequence_number', 'invitation_text')
        widgets = {
            'registration_email_subject': forms.Textarea(attrs={'class': 'form-control', 'cols': 40, 'rows': 2}),
        }


class ExperimentParameterValueForm(forms.ModelForm):
    required_css_class = 'required'

    def __init__(self, post_dict=None, instance=None, pk=None, **kwargs):
        if instance is None and pk is not None and pk != '-1':
            instance = ExperimentParameterValue.objects.get(pk=pk)
        super(ExperimentParameterValueForm, self).__init__(post_dict, instance=instance, **kwargs)

        self.fields['parameter'].queryset = self.fields[
            'parameter'].queryset.filter(scope='experiment')

        for name, field in self.fields.items():
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

        if post_dict:
            self.request_type = post_dict.get('request_type')

    def save(self, commit=True):
        epv = super(ExperimentParameterValueForm, self).save(commit=False)
        if self.request_type == 'delete':
            logger.warn("Deleting experiment parameter value %s", epv)
            epv.delete()
        elif commit:
            epv.save()
        return epv

    class Meta:
        model = ExperimentParameterValue
        exclude = ('last_modified', 'date_created')
        widgets = {
            'string_value': forms.Textarea(attrs={'cols': 40, 'rows': 3}),
            'experiment_configuration': forms.HiddenInput
        }


class RoundConfigurationForm(forms.ModelForm):
    required_css_class = 'required'

    def __init__(self, post_dict=None, instance=None, pk=None, **kwargs):
        self.old_sequence_number = None
        if instance is None and pk is not None and pk != '-1':
            instance = RoundConfiguration.objects.get(pk=pk)
            self.old_sequence_number = instance.sequence_number
        super(RoundConfigurationForm, self).__init__(post_dict, instance=instance, **kwargs)

        for name, field in self.fields.items():
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

            help_text = field.help_text
            field.help_text = None
            if help_text != '':
                field.widget.attrs.update(
                    {'class': 'has-popover', 'data-content': help_text, 'data-placement': 'right',
                     'data-container': 'body'})

        if post_dict:
            self.request_type = post_dict.get('request_type')

    def save(self, commit=True):
        rc = super(RoundConfigurationForm, self).save(commit=False)
        rc.update_sequence_number(self.old_sequence_number)

        if self.request_type == 'delete':
            logger.warn("Deleting round configuration %s", rc)
            rc.delete()
        elif commit:
            rc.save()
        return rc

    class Meta:
        model = RoundConfiguration
        exclude = ('last_modified', 'date_created', 'template_filename', 'instructions',
                   'debriefing')
        widgets = {
            'experiment_configuration': forms.HiddenInput
        }


class RoundParameterValueForm(forms.ModelForm):
    required_css_class = 'required'

    def __init__(self, post_dict=None, instance=None, pk=None, **kwargs):
        if instance is None and pk is not None and pk != '-1':
            instance = RoundParameterValue.objects.get(pk=pk)
        super(RoundParameterValueForm, self).__init__(post_dict, instance=instance, **kwargs)

        self.fields['parameter'].queryset = self.fields['parameter'].queryset.filter(scope='round')

        for name, field in self.fields.items():
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs['data-bind'] = 'checked: %s' % name
            else:
                field.widget.attrs['data-bind'] = 'value: %s' % name

        if post_dict:
            self.request_type = post_dict.get('request_type')

    def save(self, commit=True):
        rpv = super(RoundParameterValueForm, self).save(commit=False)
        if self.request_type == 'delete':
            logger.warn("Deleting round parameter value %s", rpv)
            rpv.delete()
        elif commit:
            rpv.save()
        return rpv

    class Meta:
        model = RoundParameterValue
        exclude = ('last_modified', 'date_created')
        widgets = {
            'string_value': forms.Textarea(attrs={'cols': 40, 'rows': 3}),
            'round_configuration': forms.HiddenInput
        }


class EmailListField(forms.CharField):
    widget = forms.Textarea

    def clean(self, value):
        super(EmailListField, self).clean(value)
        lines = value.split('\n')
        # emails = email_separator_re.split(value)
        if not lines:
            raise ValidationError(_(u'You must enter at least one email address.'))
        emails = []
        for line in lines:
            # check for emails in the form of Allen T Lee <allen.t.lee@asu.edu>
            (full_name, email_address) = email.utils.parseaddr(line)
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
    required_css_class = 'required'

    experiment_pk = forms.IntegerField(widget=widgets.HiddenInput)
    start_date = forms.DateField(required=False,
                                 help_text=_('''Date this experiment should activate and start.
                                 Used for multi-day experiments with daily rounds'''))
    experiment_password = forms.CharField(
        required=False,
        min_length=3,
        help_text=_('Participant login password. If blank, a unique password will be generated for each participant.'))
    institution_name = forms.CharField(min_length=3, label="Institution name",
                                       required=False, initial='Arizona State University',
                                       widget=autocomplete_light.TextWidget(InstitutionAutocomplete),
                                       help_text=_('Institution to associate with these participants.'))
    registration_email_from_address = forms.EmailField(
        widget=EmailInput(),
        label=_('Sender email'),
        help_text=_("Email address to use in the from field of the registration email"))
    sender = forms.CharField(required=False, label='Sender name', initial="The vcweb development team",
                             help_text=_('Name to use when signing off the registration email'),)
    registration_email_subject = forms.CharField(min_length=3, label="Email subject",
                                                 help_text=_('Subject line for the registration email'))
    registration_email_text = forms.CharField(
        required=False, widget=forms.Textarea, label="Email body",
        help_text=_('Custom text placed at the start of the message before generated registration text.'))

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
    username_suffix = forms.CharField(
        min_length=1, initial='asu',
        help_text=_('Appended to every generated username before the "@" symbol, e.g., s1asu@mailinator.com'))
    email_suffix = forms.CharField(
        min_length=3, initial='mailinator.com',
        help_text=_('''An email suffix without the "@" symbol.  Generated participants will receive usernames of
                       s1<username_suffix>@<email_suffix>..sn<username_suffix>@<email_suffix>. For example, if you
                       register 20 participants with a username suffix of asu and an email suffix of mailinator.com, the
                       system will generate 20 participants with usernames ranging from s1asu@mailinator.com,
                       s2asu@mailinator.com, s3asu@mailinator.com, ... s20asu@mailinator.com.'''))
    number_of_participants = forms.IntegerField(min_value=2, initial=10, widget=NumberInput(attrs={'min': 2}))


class RegisterEmailListParticipantsForm(RegisterParticipantsForm):
    send_email = forms.BooleanField(
        initial=True,
        help_text=_('Check this box to send registration emails to the participants.'))
    participant_emails = EmailListField(
        label="Participant emails",
        help_text=_('A newline delimited list of emails to register as participants for this experiment.'))


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
    message = forms.CharField(required=False)


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


class UpdateExperimentForm(forms.Form):
    # FIXME: turn action into a Choices field
    action = forms.CharField(max_length=64)
    experiment_id = forms.IntegerField(widget=forms.HiddenInput)


class LikeForm(forms.Form):
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)


class CommentForm(forms.Form):
    message = forms.CharField(max_length=512)
    target_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)


class SingleIntegerDecisionForm(forms.Form):
    integer_decision = forms.IntegerField(required=True, min_value=0)
    participant_group_id = forms.IntegerField(
        required=True, widget=forms.widgets.HiddenInput)
    submitted = forms.BooleanField(
        required=False, widget=forms.widgets.HiddenInput)


class AntiSpamForm(forms.Form):
    timestamp = forms.IntegerField(widget=forms.HiddenInput)
    security_hash = forms.CharField(min_length=40, max_length=40, widget=forms.HiddenInput)
    # honeypot
    contact_number = forms.CharField(required=False, widget=forms.TextInput, label='')

    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        initial.update(self.generate_security_data())
        kwargs["initial"] = initial
        super(AntiSpamForm, self).__init__(*args, **kwargs)

    def security_errors(self):
        """Return just those errors associated with security"""
        errors = ErrorDict()
        for f in ["contact_number", "timestamp", "security_hash"]:
            if f in self.errors:
                errors[f] = self.errors[f]
        return errors

    def clean_security_hash(self):
        """Check the security hash."""
        security_hash_dict = {
            'timestamp': self.data.get("timestamp", ""),
        }
        expected_hash = self.generate_security_hash(**security_hash_dict)
        actual_hash = self.cleaned_data["security_hash"]
        if expected_hash != actual_hash:
            raise forms.ValidationError("Security hash check failed.")
        return actual_hash

    def clean_timestamp(self):
        """Make sure the timestamp isn't too far (> 2 hours) in the past or too close (< 5 seg)."""
        ts = self.cleaned_data["timestamp"]
        difference = time.time() - ts
        if difference > (2 * 60 * 60) or difference < 5:
            raise forms.ValidationError("Timestamp check failed")
        return ts

    def generate_security_data(self):
        """Generate a dict of security data for "initial" data."""
        timestamp = int(time.time())
        security_dict = {
            'timestamp': str(timestamp),
            'security_hash': self.initial_security_hash(timestamp),
        }
        return security_dict

    def initial_security_hash(self, timestamp):
        """
        Generate the initial security hash from a (unix) timestamp.
        """

        initial_security_dict = {
            'timestamp': str(timestamp),
        }
        return self.generate_security_hash(**initial_security_dict)

    def generate_security_hash(self, timestamp):
        """Generate a (SHA1) security hash from the provided info."""
        info = (timestamp, settings.SECRET_KEY)
        return sha1("".join(info)).hexdigest()

    def clean_contact_number(self):
        """Check that nothing's been entered into the honeypot."""
        value = self.cleaned_data["contact_number"]
        if value:
            raise forms.ValidationError(self.fields["contact_number"].label)
        return value


class AntiSpamContactForm(AntiSpamForm, ContactForm):

    def from_email(self):
        return self.cleaned_data.get('email', settings.DEFAULT_FROM_EMAIL)


class BugReportForm(AntiSpamForm):

    def __init__(self, *args, **kwargs):
        super(BugReportForm, self).__init__(*args, **kwargs)

    title = forms.CharField(max_length=512)
    body = forms.CharField(widget=forms.Textarea, label=u'Description')
