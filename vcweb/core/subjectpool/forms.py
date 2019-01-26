import logging


from django import forms
from django.forms import widgets, CheckboxInput, ModelForm
from django.utils.translation import ugettext_lazy as _
from dal import autocomplete

from vcweb.core.forms import NumberInput
from vcweb.core.models import (ParticipantSignup, ExperimentSession, Institution)


logger = logging.getLogger(__name__)

HOUR_CHOICES = [(i, i) for i in range(0, 23)]
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


class ExperimentSessionForm(forms.ModelForm):
    def __init__(self, post_dict=None, instance=None, pk=None, user=None, **kwargs):
        if instance is None and pk is not None and pk != '-1':
            instance = ExperimentSession.objects.get(pk=pk)
        super(ExperimentSessionForm, self).__init__(post_dict, instance=instance, **kwargs)
        self.user = user
        if post_dict:
            self.request_type = post_dict.get('request_type')

    def save(self, commit=True):
        es = super(ExperimentSessionForm, self).save(commit=False)
        if self.request_type == 'delete':
            logger.warn("Deleting experiment session %s", es)
            es.delete()
        else:
            es.creator = self.user
            if commit:
                es.save()
        return es

    class Meta:
        model = ExperimentSession
        exclude = ('creator', 'date_created', 'invitation_text')


class SessionInviteForm(forms.Form):
    GENDER_CHOICES = (('A', 'All'), ('M', 'Male'), ('F', 'Female'),)

    number_of_people = forms.IntegerField(
        help_text=_("Number of participants to invite to the selected experiment session(s)"),
        widget=NumberInput(attrs={'value': 0, 'class': 'input-mini'}))
    only_undergrad = forms.BooleanField(
        help_text=_("Limit to self-reported undergraduate students"),
        widget=CheckboxInput(attrs={'checked': True}), required=False)
    port_of_mars = forms.BooleanField(
        help_text=_("Limit to Port of Mars Signups"),
        required=False
    )
    gender = forms.ChoiceField(choices=GENDER_CHOICES)
    affiliated_institution = forms.ModelChoiceField(
        queryset=Institution.objects.all(),
        required=False,
        initial=1,
        widget=autocomplete.ModelSelect2(
            url='core:institution-autocomplete',
            attrs={
                'data-placeholder': 'Institution name',
                'data-minimum-input-length': 3,
            }
        )
    )
    invitation_subject = forms.CharField(widget=widgets.TextInput())
    invitation_text = forms.CharField(widget=widgets.Textarea(attrs={'rows': '4'}))


class ParticipantAttendanceForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(ParticipantAttendanceForm, self).__init__(*args, **kwargs)
        self.fields['attendance'].widget.attrs['class'] = 'form-control input-sm'

    class Meta:
        model = ParticipantSignup
        fields = ['attendance']
