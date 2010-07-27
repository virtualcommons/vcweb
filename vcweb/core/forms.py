'''
Core Forms

@author: alllee
'''
from django import forms
from django.forms import widgets

#from django.forms import ModelForm
#from vcweb.core.models import Experimenter

class RegistrationForm(forms.Form):
    email = forms.EmailField(required=True, widget=widgets.TextInput(attrs={'class':'required email'}))
    password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs={'class':'required '}))
    confirm_password = forms.CharField(required=True, widget=widgets.PasswordInput(attrs={'class':'required'}))


    