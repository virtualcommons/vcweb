import random

from vcweb.core.models import *


def pollutify(experiment, pollution_amount, resource_string_length):
    for group in experiment.group_set.all():
        resource_index = xrange(1, (resource_string_length + 1))
        pollution_locations = sorted(
            random.sample(resource_index, pollution_amount))
        pollution_parameter = Parameter.objects.get(
            name='sanitation.pollution')
        round_data = group.get_round_data()
        for i, location in enumerate(pollution_locations):
            # generate a GroupRoundDataValue for this location (this can be shortened)
            # round_data.group_data_value_set.create(group=group, parameter=pollution_parameter, value=location)
            grdv = group.data_value_set.create(
                round_data=round_data, parameter=pollution_parameter, value=location)
        #grdv = GroupRoundDataValue.objects.create(group=group, round_data=round_data, parameter=pollution_parameter, value=location)
            logger.debug("grdv is %s", grdv)


def pollution_url_maker(pk, pollution_symbol):
    pollution_url = "<a id='%d' class='pollution' href='#'>%s</a>" % (
        pk, pollution_symbol)
    # pollution_url = '<a id='' href="#"> ' + pollution_symbol + ' </a>'
    # use jQuery to bind a click handler to all DOM elements with class='pollution',
    # look at jquery selector documentation
    #$('.pollution').click(function() {
    #    ajax call here
    #    });
    # will probably need to use jQuery .delegate or .live to handle this
    # properly
    return pollution_url

# returns a new string with pollution embedded in it


def get_pollution_string(group, resource_string, pollution_symbol="@"):
    resource_string_list = list(resource_string)
# XXX: since we're inserting more than one character we need to be careful not to insert into a location where
# we appended text..
    for i, grdv in enumerate(GroupRoundDataValue.objects.filter(group=group, round_data=group.get_round_data(), is_active=True)):
        pollution_url = pollution_url_maker(grdv.pk, pollution_symbol)
        offset = len(pollution_url)
        offset_location = grdv.value + (i * offset)
        resource_string_list.insert(offset_location, pollution_url)
    return ''.join(resource_string_list)
