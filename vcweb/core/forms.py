'''
Core Forms

@author: alllee
'''
from django import forms
from django.forms import widgets

#from django.forms import ModelForm
#from vcweb.core.models import Experimenter
EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class RegistrationForm(forms.Form):
    email = forms.EmailField(required=True, widget=widgets.TextInput(attrs=EMAIL_ATTRIBUTES))
    password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    # these are hidden unless they check "experimenter request"
    experimenter = forms.BooleanField()
    first_name = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(required=True, widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))



class LoginForm(forms.Form):
    email = forms.EmailField(required=True, widget=widgets.TextInput(attrs=EMAIL_ATTRIBUTES))
    password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

