from django import forms

class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput)
