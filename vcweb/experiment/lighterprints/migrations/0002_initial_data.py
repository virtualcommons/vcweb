# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


_activity_dict_list = [
    {
        "display_name": "Eat locally grown food for lunch",
        "description": "The food we eat comes from all over the world. How much CO2 this emits depends on your specific location and menu. On average, a person in the USA can save 1,400 pounds of CO2 per year by switching to locally grown food. We assume that one lunch is equivalent of 1.5 pounds of CO2 saved.",
        "available_all_day": False,
        "url": "http://www.huffingtonpost.com/bill-chameides/carbon-savings-at-home_b_113551.html",
        "level": 1,
        "group_activity": False,
        "summary": "Less energy is used for transportation when only locally grown food is consumed",
        "cooldown": 1,
        "savings": "1.50",
        "points": 15,
        "icon": "lighterprints/activity-icons/80-shopping-cart_1.png",
        "personal_benefits": "Locally grown food often contains less preservatives and is fresher, making it a healthier and tastier choice. ",
        "is_public": True,
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
        "cooldown": 1,
        "savings": "0.98",
        "points": 10,
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
        "cooldown": 1,
        "savings": "0.31",
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
        "cooldown": 1,
        "savings": "9.40",
        "points": 94,
        "icon": "lighterprints/activity-icons/81-dashboard_1.png",
        "is_public": True,
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
        "is_public": True,
        "name": "bike-or-walk"
    },
]


def create_activities(apps, schema_editor):
    Activity = apps.get_model('lighterprints', 'Activity')
    for activity_dict in _activity_dict_list:
        Activity.objects.create(**activity_dict)


class Migration(migrations.Migration):

    dependencies = [
        ('lighterprints', '0001_initial'),
    ]

    operations = [
    ]
