#!/bin/bash
test -f vcweb.db && rm vcweb.db
./manage.py syncdb --noinput
./manage.py loaddata test_users_participants
./manage.py loaddata forestry_test_data

