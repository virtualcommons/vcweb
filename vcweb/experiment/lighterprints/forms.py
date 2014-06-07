from django import forms
from localflavor.us.forms import USZipCodeField


class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput)


class GreenButtonUploadFileForm(forms.Form):
    zipcode = USZipCodeField()
    file = forms.FileField()
