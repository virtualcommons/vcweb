'''
Core Forms

@author: alllee
'''
from django import forms
from django.forms import widgets

#from django.forms import ModelForm
#from vcweb.core.models import Experimenter
REQUIRED_EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class RegistrationForm(forms.Form):
    email = forms.EmailField(required=True, widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    first_name = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password != confirm_password:
            raise forms.ValidationError("Please make sure your passwords match.")
        return self.cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(required=True, widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

