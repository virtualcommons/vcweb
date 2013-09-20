from django import forms
from django.forms import widgets, ValidationError


REQUIRED_ATTRIBUTES = {'class': 'required'}


class SessionForm(forms.Form):
    pk = forms.IntegerField(widgets.TextInput())
    experiment_meta_data = forms.IntegerField(widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    start_date = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    end_date = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    capacity = forms.IntegerField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))