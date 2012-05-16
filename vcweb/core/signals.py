from django.dispatch import Signal


experiment_started = Signal(providing_args=["experiment", "time", "experimenter"])
participant_added = Signal(providing_args=['experiment', 'time', 'participant_group_relationship'])
round_started = Signal(providing_args=["experiment", 'time', 'round_configuration'])
round_ended = Signal(providing_args=['experiment', 'time', 'round_configuration'])
minute_tick = Signal(providing_args=['time'])
hour_tick = Signal(providing_args=['time'])
midnight_tick = Signal(providing_args=['time'])

post_login = Signal(providing_args=['user'])
post_logout = Signal(providing_args=['user'])
