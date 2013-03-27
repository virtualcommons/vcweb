from django import forms

__author__ = 'diegogalafassi'

class ChatPreferenceForm (forms.Form):
    participant_group_id = forms.IntegerField()
    chat_within_group = forms.BooleanField(default=False)
    chat_between_group = forms.BooleanField(default=False)
