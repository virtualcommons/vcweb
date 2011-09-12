from django import forms

class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(required=True, widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(required=True, widget=forms.HiddenInput)

