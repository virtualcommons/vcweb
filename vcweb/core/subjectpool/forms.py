import logging

from django import forms

from django.forms import widgets, CheckboxInput, ModelForm
from django.utils.translation import ugettext_lazy as _
import autocomplete_light

from vcweb.core.autocomplete_light_registry import InstitutionAutocomplete

from vcweb.core.forms import NumberInput
from vcweb.core.models import (ParticipantSignup)


logger = logging.getLogger(__name__)

HOUR_CHOICES = [(i, i) for i in xrange(0, 23)]
MIN_CHOICES = [(i, i) for i in (0, 15, 30, 45)]

class CancelSignupForm(forms.Form):
    pk = forms.IntegerField()

    def clean_pk(self):
        data = self.cleaned_data['pk']
        try:
            self.signup = ParticipantSignup.objects.select_related('invitation__experiment_session',
                                                                   'invitation__participant').get(pk=data)
        except ParticipantSignup.DoesNotExist:
            raise forms.ValidationError(_("No signup found with pk %s" % data))
        return data


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
    location = forms.CharField(widget=widgets.TextInput(), required=False)
    request_type = forms.CharField(widget=widgets.TextInput())

    def clean(self):
        data = super(SessionForm, self).clean()
        pk = data.get('pk')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        location = data.get('location')
        request_type = data.get('request_type')

        if not pk:
            logger.error("No experiment session pk found: %s", data)
            raise forms.ValidationError(_("No experiment session pk was found"))
        else:
            # logger.debug(data)
            if request_type != 'delete':
                if not start_date or not end_date:
                    raise forms.ValidationError(_("Please enter a start and end date"))
                if not location:
                    raise forms.ValidationError(_("Please enter a location for the experiment session"))
        return data


class SessionInviteForm(forms.Form):
    number_of_people = forms.IntegerField(widget=NumberInput(attrs={'value': 0, 'class': 'input-mini'}))
    only_undergrad = forms.BooleanField(widget=CheckboxInput(attrs={'checked': True}))
    affiliated_university = forms.CharField(
        widget=autocomplete_light.TextWidget(InstitutionAutocomplete, attrs={'value': 'Arizona State University'}))
    invitation_subject = forms.CharField(widget=widgets.TextInput())
    invitation_text = forms.CharField(widget=widgets.Textarea(attrs={'rows': '4'}))


class ParticipantAttendanceForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ParticipantAttendanceForm, self).__init__(*args, **kwargs)
        self.fields['attendance'].widget.attrs['class'] = 'form-control input-sm'

    class Meta:
        model = ParticipantSignup
        fields = ['attendance']