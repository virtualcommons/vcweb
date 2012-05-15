from django import forms
from django.contrib.localflavor.us.forms import USZipCodeField
from bootstrap.forms import BootstrapForm, Fieldset

class ActivityForm(forms.Form):
    activity_id = forms.IntegerField(widget=forms.HiddenInput)
    participant_group_id = forms.IntegerField(widget=forms.HiddenInput)
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput)
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput)

class GreenButtonUploadFileForm(BootstrapForm):
    class Meta:
        layout = {
                Fieldset("Please enter your zipcode and a Green Button Data file from your energy provider",
                    "zipcode", "file",
                    ),
                }

    zipcode = USZipCodeField()
    file = forms.FileField()
