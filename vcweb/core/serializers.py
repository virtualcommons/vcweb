from rest_framework import serializers
from .models import (Experiment, RoundData, ChatMessage)


class ChatMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ChatMessage


class ExperimentRoundDataSerializer(serializers.ModelSerializer):
    chat_messages = ChatMessageSerializer(many=True)

    class Meta:
        model = RoundData


class ExperimentSerializer(serializers.ModelSerializer):

    experimenter = serializers.StringRelatedField()
    round_status_label = serializers.CharField(source='status_label')
    round_sequence_label = serializers.CharField(source='sequence_label')
    participant_count = serializers.IntegerField(source='number_of_participants')
    url = serializers.URLField(source='experimenter_url')

    class Meta:
        model = Experiment
        fields = ('id', 'round_status_label', 'round_sequence_label', 'experimenter', 'name',
                  'experiment_metadata', 'experiment_configuration', 'status', 'date_created', 'last_modified',
                  'date_activated', 'is_active', 'is_archived', 'exchange_rate', 'start_date',
                  'time_remaining', 'participant_count', 'number_of_ready_participants',
                  'registration_email_subject', 'registration_email_text', 'current_round_start_time', 'url',)
