from django import forms
from django.forms import widgets
from django.utils.translation import ugettext_lazy as _

from vcweb.core.models import Participant, Experimenter

REQUIRED_EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class RegistrationForm(forms.Form):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    first_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_("This email address is already in our system."))


    def clean_confirm_password(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password != confirm_password:
            raise forms.ValidationError(_("Please make sure your passwords match."))
        return self.confirm_password


class LoginForm(forms.Form):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

class ParticipantAccountForm(forms.ModelForm):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    class Meta:
        model = Participant

class ExperimenterAccountForm(forms.ModelForm):
    class Meta:
        model = Experimenter
