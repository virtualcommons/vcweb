#!/bin/bash

cd /code;
./deploy/runit/wait-for-it.sh db:5432 -t 30 -- invoke test --tests="$@" --coverage
