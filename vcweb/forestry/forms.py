from django import forms

REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class HarvestDecisionForm(forms.Form):
    harvest_decision = forms.IntegerField(required=True, min_value=0, max_value=5)
    participant_group_id = forms.IntegerField(required=True, widget=forms.widgets.HiddenInput)

    def clean(self):
        harvest_decision = self.cleaned_data['harvest_decision']
        try:
            # only testing for integer-ness
            int(harvest_decision)
            return self.cleaned_data
        except:
            raise forms.ValidationError("Invalid harvest decision %s" % harvest_decision)
