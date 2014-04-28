from django import forms

__author__ = 'diegogalafassi'

class ChatPreferenceForm (forms.Form):
    participant_group_id = forms.IntegerField(widget=forms.widgets.HiddenInput)
    chat_within_group = forms.BooleanField(initial=False, required=False)
    chat_between_group = forms.BooleanField(initial=False, required=False)
