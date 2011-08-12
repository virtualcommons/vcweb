from django import forms

from django.utils.html.escape import escape


class ChatForm(forms.Form):
    message = forms.CharField(required=True, max_length=512)
    participant_group_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    def clean_message(self):
        return escape(self.cleaned_data['message'])


class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

