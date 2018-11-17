#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

DEPLOY=${1:-dev} # dev | prod
CONFIG_INI=deploy/conf/config.ini
CONFIG_TEMPLATE_INI=deploy/conf/config.template.ini
POSTGRES_PASSWORD_FILE=deploy/conf/postgres_password

export DB_USER=vcweb
export DB_NAME=vcweb
export DB_HOST=db
export DB_PORT=5432
export DB_PASSWORD=$(head /dev/urandom | tr -dc '[:alnum:]' | head -c42)
export DJANGO_SECRET_KEY=$(head /dev/urandom | tr -dc '[:alnum:]' | head -c42)

if [ -f "$CONFIG_INI" ]; then
    echo $PWD
    echo "Config file config.ini already exists"
    echo "Replacing $CONFIG_INI will change the db password. Continue?"
    select response in "Yes" "No"; do
        case "${response}" in
            Yes) break;;
            No) echo "Aborting build"; exit;;
        esac
    done
    backup_name=config-backup-$(date '+%Y-%m-%d.%H-%M-%S').ini
    mv ${CONFIG_INI} ./deploy/conf/${backup_name}
    echo "Backed up old config file to $backup_name"
fi

echo "Creating config.ini for ${DEPLOY}"
cat "$CONFIG_TEMPLATE_INI" | envsubst > "$CONFIG_INI"
echo $DB_PASSWORD > ${POSTGRES_PASSWORD_FILE}

./compose ${DEPLOY}
docker-compose up -d db
sleep 10;
docker-compose exec db bash -c "psql -U ${DB_USER} -d ${DB_NAME} -c \"ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}'\""
echo "Successfully changed postgres password"
docker-compose build --pull
