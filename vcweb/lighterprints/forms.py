from django import forms


class ChatForm(forms.Form):
    message = forms.CharField(required=True, max_length=512)
    participant_group_relationship_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    participant_group_relationship_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

