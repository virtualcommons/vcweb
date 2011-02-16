from django import forms

REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class HarvestDecisionForm(forms.Form):
    harvest_decision = forms.IntegerField(required=True, min_value=0, max_value=5)

    def clean(self):
        # need to determine if this harvest decision is allowable given the current resource level
        # for this experiment.
        harvest_decision = self.cleaned_data['harvest_decision']
        if 0 <= harvest_decision <= 5:
            return self.cleaned_data
        raise forms.ValidationError("Invalid harvest decision %s" % harvest_decision)


