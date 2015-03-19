from django.dispatch import Signal


experiment_started = Signal(providing_args=["experiment", "timestamp", "experimenter"])
participant_added = Signal(providing_args=['experiment', 'timestamp', 'participant_group_relationship'])
round_started = Signal(providing_args=["experiment", 'timestamp', 'round_configuration'])
round_ended = Signal(providing_args=['experiment', 'timestamp', 'round_configuration'])
minute_tick = Signal(providing_args=['time'])
hour_tick = Signal(providing_args=['time'])
system_daily_tick = Signal(providing_args=['timestamp'])
system_weekly_tick = Signal(providing_args=['timestamp'])
system_monthly_tick = Signal(providing_args=['timestamp'])

post_login = Signal(providing_args=['user'])
post_logout = Signal(providing_args=['user'])
