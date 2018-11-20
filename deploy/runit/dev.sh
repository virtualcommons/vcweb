#!/bin/bash

CLEAN_DATABASE=${CLEAN_DATABASE:-"false"}
DJANGO_SETTINGS_MODULE="vcweb.settings.dev"

chmod a+x /code/deploy/runit/*.sh

exec /code/deploy/runit/wait-for-it.sh db:5432 -- /code/manage.py runserver 0.0.0.0:8000
