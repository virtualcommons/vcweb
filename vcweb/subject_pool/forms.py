from django import forms
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


REQUIRED_ATTRIBUTES = {'class': 'required'}


class SessionForm(forms.Form):
    pk = forms.IntegerField(widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    experiment_meta_data = forms.IntegerField(widgets.TextInput())
    start_date = forms.CharField(widget=widgets.TextInput())
    end_date = forms.CharField(widget=widgets.TextInput())
    capacity = forms.IntegerField(widget=widgets.TextInput())
    request_type = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        data = super(forms.Form, self).clean()
        pk = data.get('pk')
        experiment_meta_data = data.get('experiment_meta_data')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        capacity = data.get('capacity')
        request_type = data.get('request_type')

        if not pk:
            raise forms.ValidationError(_("Invalid Experiment session PK"))
        else:
            logger.debug(data)
            if request_type != 'delete':
                if not experiment_meta_data or not start_date or not end_date:
                    raise forms.ValidationError(_("Pleas Fill in all the Fields"))
        return data