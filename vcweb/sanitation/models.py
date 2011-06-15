from django.db import models

import random

def pollutify(resource_string, pollution_amount, pollution_symbol, group=None):
    resource_index = xrange(1,(len(resource_string) + 1))
    pollution_locations = sorted(random.sample(resource_index, pollution_amount))
#    pollution_parameter = Parameter.objects.get(name='sanitation.pollution')
    resource_string_list = list(resource_string)
    offset = len(pollution_symbol)
    for i, location in enumerate(pollution_locations):
# generate a GroupRoundDataValue for this location (this can be shortened)
#        grdv = GroupRoundDataValue.objects.create(group=group, round_data=group.current_round_data, parameter=pollution_parameter, value=location)
#        logger.debug("grdv is %s", grdv)
# FIXME: since we're inserting more than one character we need to be careful not to insert into a location where
# we appended text..
        resource_string_list.insert(location + (i * offset), pollution_symbol)
    return ''.join(resource_string_list)



