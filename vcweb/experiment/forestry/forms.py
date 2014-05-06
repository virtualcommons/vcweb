import logging

from django import forms


logger = logging.getLogger(__name__)

class HarvestDecisionForm(forms.Form):
    harvest_decision = forms.IntegerField(required=True, min_value=0)
    participant_group_id = forms.IntegerField(required=True, widget=forms.widgets.HiddenInput)
