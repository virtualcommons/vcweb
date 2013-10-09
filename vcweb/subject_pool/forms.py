from django import forms
from django.forms import widgets, ValidationError
from vcweb.core.models import ExperimentSession
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


REQUIRED_ATTRIBUTES = {'class': 'required'}
HOUR_CHOICES = (('0', '0'),('1', '1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),('21','21'),('22','22'),('23','23'))
MIN_CHOICES = (('0','0'),('15','15'),('30','30'),('45','45'))


class SessionForm(forms.Form):
    pk = forms.IntegerField(widgets.TextInput())
    experiment_metadata_pk = forms.IntegerField(widgets.TextInput(), required=False)
    start_date = forms.CharField(widget=widgets.TextInput(), required=False)
    start_hour = forms.ChoiceField(choices=HOUR_CHOICES, required=False)
    start_min = forms.ChoiceField(choices=MIN_CHOICES, required=False)
    end_date = forms.CharField(widget=widgets.TextInput(), required=False)
    end_hour = forms.ChoiceField(choices=HOUR_CHOICES, required=False)
    end_min = forms.ChoiceField(choices=MIN_CHOICES, required=False)
    capacity = forms.IntegerField(widget=widgets.TextInput(), required=False)
    request_type = forms.CharField(widget=widgets.TextInput())

    def clean(self):
        data = super(forms.Form, self).clean()
        pk = data.get('pk')
        experiment_metadata_pk = data.get('experiment_metadata_pk')
        start_date = data.get('start_date')
        start_hour = data.get('start_hour')
        start_min = data.get('start_min')
        end_date = data.get('end_date')
        end_hour = data.get('end_hour')
        end_min = data.get('end_min')
        capacity = data.get('capacity')
        request_type = data.get('request_type')

        if not pk:
            raise forms.ValidationError(_("Invalid Experiment session PK"))
        else:
            logger.debug(data)
            if request_type != 'delete':
                if not experiment_metadata_pk or not start_date or not end_date:
                    raise forms.ValidationError(_("Please Fill in all the Fields"))
        return data


class SessionDetailForm(forms.ModelForm):
    class Meta:
        model = ExperimentSession
        fields = ('experiment_metadata', 'date_created', 'scheduled_date', 'scheduled_end_date', 'capacity')
        labels = {
            'experiment_metadata': 'Experiment',
            'scheduled_date' : 'Start Date'
        }