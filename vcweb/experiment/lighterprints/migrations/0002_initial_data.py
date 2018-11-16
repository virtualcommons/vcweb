# -*- coding: utf-8 -*-


from django.db import models, migrations


_activities = [
    {
        "display_name": "Adjust your thermostat by 2 degrees",
        "description": "Climate-controlled buildings cost a lot of energy. Adjusting the temperature by two degrees saves 2,000 pounds of CO2 a year.",
        "available_all_day": False,
        "url": "http://earthcareindiana.org/node/131",
        "level": 1,
        "group_activity": False,
        "summary": "Heating or cooling buildings less saves energy",
        "cooldown": 1,
        "savings": "5.50",
        "points": 55,
        "icon": "lighterprints/activity-icons/93-thermometer_1.png",
        "personal_benefits": "Less energy used results in savings on an electric bill. ",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "is_public": True,
        "name": "adjust-thermostat"
    },
    {
        "display_name": "Eat locally grown food for lunch",
        "description": "The food we eat comes from all over the world. How much CO2 this emits depends on your specific location and menu. On average, a person in the USA can save 1,400 pounds of CO2 per year by switching to locally grown food. We assume that one lunch is equivalent of 1.5 pounds of CO2 saved.",
        "available_all_day": False,
        "url": "http://www.huffingtonpost.com/bill-chameides/carbon-savings-at-home_b_113551.html",
        "level": 1,
        "group_activity": False,
        "summary": "Less energy is used for transportation when only locally grown food is consumed",
        "savings": "1.50",
        "points": 15,
        "icon": "lighterprints/activity-icons/80-shopping-cart_1.png",
        "personal_benefits": "Locally grown food often contains less preservatives and is fresher, making it a healthier and tastier choice. ",
        "is_public": True,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "name": "eat-local-lunch"
    },
    {
        "display_name": "Enable sleep function on your computer",
        "description": "Annual energy savings from enabling the sleep feature on a computer and monitor = 235 kWh.\r\nSavings assumes a weighted average of consumer behavior rather than assuming computers are turned off all night, as well as that the computer and monitor are ENERGY STAR rated. ",
        "available_all_day": True,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 1,
        "group_activity": False,
        "summary": "Your computer consumes less energy when it's asleep or turned off",
        "savings": "0.98",
        "points": 10,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/69-display_1.png",
        "personal_benefits": "Using the sleep function can save money on your electric bill. It also can reduce the heat produced by your computer, which may improve its lifetime. ",
        "is_public": True,
        "name": "enable-sleep-on-computer"
    },
    {
        "display_name": "Recycle materials",
        "description": "The average number of pounds of CO2 equivalent per person per year that could be saved by recycling is 6.83 pounds for glass, 18.96 pounds for plastic, and 86.05 pounds for aluminum and steel cans. This is an average of 2.15 pounds a week, or .31 pounds a day.",
        "available_all_day": True,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 1,
        "group_activity": False,
        "summary": "Recycling processes used materials into new products to prevent waste of potentially useful materials.",
        "savings": "0.31",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "points": 3,
        "icon": "lighterprints/activity-icons/51-recycle.png",
        "is_public": True,
        "name": "recycle-materials"
    },
    {
        "display_name": "Share your ride",
        "description": "We assume a car averaging 21.4 miles per gallon. CO2 emissions are 19.53 pounds per gallon and 1.5 pounds per gallon of non-CO2 CO2 equivalent emissions. This means 0.94 pounds per mile. We assume a trip length of 5 miles.\r\n\r\nIf there are N carpoolers, the savings are (N-1) / N* 4.7. Hence for N=2 persons, the savings are 2.85 pounds. More carpoolers lead to more reductions.",
        "available_all_day": False,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 1,
        "group_activity": False,
        "summary": "Carpooling is more energy efficient than travelling alone in your car.",
        "savings": "9.40",
        "points": 94,
        "icon": "lighterprints/activity-icons/81-dashboard_1.png",
        "is_public": True,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "name": "share-your-ride"
    },
    {
        "display_name": "Bike, walk, or take public transportation when you go out",
        "description": "We assume a car averaging 22.4 miles per gallon and a trip length of 4 miles. CO2 emissions are 19.53 pounds per gallon and 1.5 pounds per gallon of non-CO2 CO2 equivalent emissions. This means 0.94 pounds per mile. ",
        "available_all_day": False,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 2,
        "group_activity": False,
        "summary": "Reduce fossil fuel consumption and emissions by not driving a car",
        "cooldown": 1,
        "savings": "7.52",
        "points": 75,
        "icon": "lighterprints/activity-icons/47-bicycle-to.png",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "is_public": True,
        "name": "bike-or-walk"
    },
    {
        "display_name": "Turn water off while brushing your teeth",
        "description": "Turning off the water while brushing saves 0.5 kWh per person per day. This assumes four minutes a day spent brushing (enough to account for brushing teeth twice daily) and typical energy use for water supply, treatment, and heating. With 1.52 CO2 per kWh this leads to a savings of 0.76 pounds of CO2 a day.",
        "available_all_day": False,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 2,
        "group_activity": False,
        "summary": "Don't leave the water running while you're brushing your teeth",
        "savings": "0.76",
        "points": 8,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/186-toothbrush_1.png",
        "name": "water-off-while-brushing-teeth"
    },
    {
        "display_name": "Turn off your computer at night",
        "description": "The average computer uses about 120 Watts (75 Watts for the screen and 45 Watts for the CPU) whether you're using it or not.\r\nOne computer left on 24 hours a day will cause 1,500 pounds of CO2 to be emitted into the atmosphere.",
        "available_all_day": False,
        "url": "http://sustainability.tufts.edu/",
        "level": 2,
        "group_activity": False,
        "summary": "Save energy and turn off your computer when it's not needed.",
        "cooldown": 1,
        "savings": "1.37",
        "points": 14,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/126-moon_1.png",
        "is_public": True,
        "name": "computer-off-night"
    },
    {
        "display_name": "Replace beef with poultry",
        "description": "Replacing the protein you get from beef with poultry can save you 1,555 pounds of CO2 emissions annually. Per day, this switch leads to 4.26 pounds of CO2 savings.",
        "available_all_day": False,
        "url": "http://www.simplesteps.org/food/shopping-wise/co2-smackdown-step-6-trimming-out-beef-and-pork",
        "level": 2,
        "group_activity": False,
        "summary": "Beef production is very energy intensive",
        "cooldown": 1,
        "savings": "4.26",
        "points": 43,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/109-chicken_1.png",
        "is_public": True,
        "name": "no-beef"
    },
    {
        "display_name": "Recycle paper",
        "description": "The average number of pounds of CO2 equivalent per person per year that could be saved by recycling paper is 14.86 pounds for magazines, 89.76 pounds for newspapers, and 100 pounds for junk mail. These add up to 0.56 pounds per day.",
        "available_all_day": True,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 2,
        "group_activity": False,
        "summary": "Saving paper resources and production by recycling",
        "cooldown": 1,
        "savings": "0.56",
        "points": 6,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/166-newspaper_1.png",
        "is_public": True,
        "name": "recycle-paper"
    },
    {
        "display_name": "Air dry your clothes",
        "description": "Air drying your clothes saves 723 pounds of CO2 every year, or 1.98 pounds per day.",
        "available_all_day": False,
        "url": "http://www.simplesteps.org/tools/house-savings-calculator#laundry",
        "level": 3,
        "group_activity": False,
        "summary": "Air drying your clothes saves gas or electricity",
        "cooldown": 1,
        "savings": "1.98",
        "points": 20,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/67-tshirt_1.png",
        "is_public": True,
        "name": "air-dry-clothes"
    },
    {
        "display_name": "Eat a green lunch",
        "description": "You can save 500 pounds of CO2 a year by reducing waste at lunch time. This means packing your lunch in a reusable container, using reusable/washable utensils, and don\\u2019t use paper napkins.",
        "available_all_day": False,
        "url": "http://www.savecarbon.org/activity_form/lunches",
        "level": 3,
        "group_activity": False,
        "summary": "Reduce the amount of waste you produce at lunch time.",
        "cooldown": 1,
        "savings": "1.37",
        "points": 14,
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "icon": "lighterprints/activity-icons/48-fork-and-knife_1.png",
        "personal_benefits": "You can save money by buying reusable containers and utensils once instead of buying disposable items regularly. ",
        "is_public": True,
        "name": "eat-green-lunch"
    },
    {
        "display_name": "Turn off unnecessary lights",
        "description": "The amount of CO2 saved by turning lights off is [60 watts / 1000 watts/kWh] * 1.52 pounds of CO2 per kWh, which equals 0.09 pounds of CO2 per bulb per hour. Assuming 5 bulbs are turned off for 5 hours, this saves 2.28 pounds of CO2 per day.",
        "available_all_day": False,
        "url": "http://www.epa.gov/climatechange/kids/calc/index.html",
        "level": 3,
        "group_activity": False,
        "summary": "Turning lights off in areas that don't need them saves energy.",
        "cooldown": 1,
        "savings": "2.28",
        "points": 23,
        "icon": "lighterprints/activity-icons/84-lightbulb_1.png",
        "personal_benefits": "Turning lights off can save you money on your electric bill. Since lights give off heat, turning them off can also help keep rooms cooler. ",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "is_public": True,
        "name": "lights-off"
    },
    {
        "display_name": "Eat a vegan breakfast",
        "description": "A plant-based diet saves 1,608 pounds of CO2 per year compared to the average diet.",
        "available_all_day": False,
        "url": "http://www.simplesteps.org/tools/house-savings-calculator#diet",
        "level": 3,
        "group_activity": False,
        "summary": "Raising animals for meat is resource intensive",
        "cooldown": 1,
        "savings": "4.41",
        "points": 44,
        "icon": "lighterprints/activity-icons/125-food_1.png",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "is_public": True,
        "name": "eat-vegan-breakfast"
    },
    {
        "display_name": "Wash your clothes with cold water",
        "description": "You can save 400 pounds of CO2 a year by washing all your clothes with cold water.",
        "available_all_day": False,
        "url": "http://ase.org/efficiencynews/energy-efficient-laundry-wash-clothes-cold-water-save-energy",
        "level": 3,
        "group_activity": False,
        "summary": "Save energy by not heating water",
        "cooldown": 1,
        "savings": "1.10",
        "points": 2,
        "icon": "lighterprints/activity-icons/24-washing-new.png",
        "lft": 0,
        "rght": 0,
        "tree_id": 0,
        "is_public": True,
        "name": "cold-water-wash"
    },
]


def create_activities(apps, schema_editor):
    Activity = apps.get_model('lighterprints', 'Activity')
    ActivityAvailability = apps.get_model(
        'lighterprints', 'ActivityAvailability')
    Activity.objects.bulk_create(
        [Activity(**activity_dict) for activity_dict in _activities]
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='adjust-thermostat'),
        start_time='06:00:00',
        end_time='08:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='eat-local-lunch'),
        start_time='12:00:00',
        end_time='14:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='enable-sleep-on-computer'),
        start_time='00:00:00',
        end_time='23:59:59',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='recycle-materials'),
        start_time='00:00:00',
        end_time='23:59:59',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='share-your-ride'),
        start_time='08:00:00',
        end_time='10:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='share-your-ride'),
        start_time='16:00:00',
        end_time='18:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='bike-or-walk'),
        start_time='18:00:00',
        end_time='23:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='computer-off-night'),
        start_time='00:00:00',
        end_time='08:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='no-beef'),
        start_time='18:00:00',
        end_time='19:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='recycle-paper'),
        start_time='00:00:00',
        end_time='23:59:59',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='water-off-while-brushing-teeth'),
        start_time='07:00:00',
        end_time='09:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='water-off-while-brushing-teeth'),
        start_time='22:00:00',
        end_time='23:59:59',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='air-dry-clothes'),
        start_time='00:00:00',
        end_time='07:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='cold-water-wash'),
        start_time='16:00:00',
        end_time='23:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='eat-green-lunch'),
        start_time='12:00:00',
        end_time='14:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='lights-off'),
        start_time='18:00:00',
        end_time='23:00:00',
    )
    ActivityAvailability.objects.create(
        activity=Activity.objects.get(name='eat-vegan-breakfast'),
        start_time='07:00:00',
        end_time='09:00:00',
    )

_parameters = [
    {
        "name": "participant_level",
        "type": "int",
        "description": "The given participant's personal footprint level, updated nightly",
        "display_name": "Participant Level",
        "scope": "participant"
    },
    {
        "display_name": "Unlocked Activity",
        "name": "activity_unlocked",
        "class_name": "lighterprints.Activity",
        "default_value_string": "",
        "scope": "participant",
        "type": "foreignkey",
        "description": "The referenced Activity is unlocked for the given participant"
    },
    {
        "display_name": "Activity Performed",
        "name": "activity_performed",
        "class_name": "lighterprints.Activity",
        "type": "foreignkey",
        "description": "The referenced Activity has been performed by the given participant",
        "scope": "participant"
    },
    {
        "name": "footprint_level",
        "display_name": "Group level",
        "type": "int",
        "description": "The given group's footprint level.",
        "scope": "group"
    },
    {
        "display_name": "Available activity",
        "name": "available_activity",
        "type": "foreignkey",
        "scope": "round",
        "description": "The referenced Activity is available in the given round for all participants in the associated experiment",
    },
    {
        "display_name": "Experiment completed",
        "name": "experiment_completed",
        "type": "boolean",
        "scope": "group",
        "description": "The given group has completed the experiment.",
    },
    {
        "display_name": "Lighter Footprints Treatment Type",
        "name": "lfp_treatment_type",
        "type": "enum",
        "scope": "experiment",
        "enum_choices": "LEADERBOARD, NO_LEADERBOARD, HIGH_SCHOOL, LEVEL_BASED",
        "description": "Lighter Footprints Treatment Type to distinguish between the different Lighter Footprints Experiments"
    },
    {
        'display_name': 'Lighter Footprints Linear Public Good',
        "name": "lfp_linear_public_good",
        "description": '''Boolean toggle signifying whether or not this experiment is a linear public good experiment
        where each participant's payoff is entirely dependent on their contributions as opposed to surpassing a threshold or
        advancing in level.''',
        "type": "boolean",
        "scope": "experiment",
    },
    {
        'display_name': 'Display leaderboard?',
        "name": "leaderboard",
        "description": 'True if we should display a leaderboard ranking progress across all groups in the experiment.',
        "type": "boolean",
        "scope": "experiment",
    },
]


def create_lighterprints_experiment_metadata(apps, schema_editor):
    ExperimentMetadata = apps.get_model('core', 'ExperimentMetadata')
    Parameter = apps.get_model('core', 'Parameter')
    lighterprints_metadata = ExperimentMetadata.objects.create(
        description="A mobile-ready HTML5 experiment / game that educates and examines how groups of people coordinate to reach carbon emission targets.",
        title="Lighter Footprints",
        namespace="lighterprints",
    )
    for parameter_dict in _parameters:
        lighterprints_metadata.parameters.add(
            Parameter.objects.create(**parameter_dict))


class Migration(migrations.Migration):

    dependencies = [
        ('lighterprints', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_activities),
        migrations.RunPython(create_lighterprints_experiment_metadata),
    ]
