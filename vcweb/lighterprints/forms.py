from django import forms


class ChatForm(forms.Form):
    chat_message = forms.CharField(required=True, max_length=512)
    participant_group_relationship = forms.IntegerField(required=True, widget=forms.HiddenInput)
