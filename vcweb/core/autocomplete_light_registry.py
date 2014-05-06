import logging

import autocomplete_light

from vcweb.core.models import Institution, Participant

logger = logging.getLogger(__name__)


#Sets up Autocomplete functionality for Institution Field on Participant Account Profile
class InstitutionAutocomplete(autocomplete_light.AutocompleteModelBase):
    search_fields = ['name','acronym']
    autocomplete_js_attributes = {
        # This will data-autocomplete-minimum-characters which
        # will set widget.autocomplete.minimumCharacters.
        'minimum_characters': 1,
        'placeholder': 'Institution Name',
    }

autocomplete_light.register(Institution, InstitutionAutocomplete)


#Sets up autocomplete functionality for institution field on participant account profile
class ParticipantMajorAutocomplete(autocomplete_light.AutocompleteListBase):
    participants = Participant.objects.order_by('major').distinct('major').values('major')
    choices = participants.values_list('major', flat=True)
    search_fields = []
    autocomplete_js_attributes = {
        # This will data-autocomplete-minimum-characters which
        # will set widget.autocomplete.minimumCharacters.
        'minimum_characters': 1,
        'placeholder': ' ',
    }
autocomplete_light.register(Participant, ParticipantMajorAutocomplete)
