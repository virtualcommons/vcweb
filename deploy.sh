#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

ENVIRONMENT=${1:-"dev"} # dev | staging | prod
DJANGO_CONTAINER=${2:-"django"}

echo "Deploying latest build of vcweb for **${ENVIRONMENT}**"
./compose ${ENVIRONMENT}
git describe --tags >| release-version.txt;
docker-compose pull db redis nginx;
docker-compose build --pull;
docker-compose up -d;
docker-compose exec ${DJANGO_CONTAINER} inv prepare
