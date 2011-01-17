'''
Created on Aug 19, 2010

@author: alllee
'''

from django.dispatch import Signal


experiment_started = Signal(providing_args=["experiment_id", "time", "experimenter"])
round_started = Signal(providing_args=["experiment_id", 'time', 'round_configuration_id'])
round_ended = Signal(providing_args=['experiment_id', 'time', 'round_configuration_id'])
second_tick = Signal(providing_args=['time'])

post_login = Signal(providing_args=['user'])
post_logout = Signal(providing_args=['user'])
