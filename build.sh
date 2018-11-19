#!/bin/bash

# invoke via ./build.sh (dev|prod)

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
export DJANGO_SECRET_KEY=$(head /dev/urandom | tr -dc '[:alnum:]' | head -c90)

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
    BACKUP_NAME=config-backup-$(date '+%Y-%m-%d.%H-%M-%S').ini
    mv ${CONFIG_INI} ./deploy/conf/${BACKUP_NAME}
    echo "Backed up old config file to ${BACKUP_NAME}"
fi

echo "Creating config.ini for ${DEPLOY}"
cat "$CONFIG_TEMPLATE_INI" | envsubst > "$CONFIG_INI"
echo -e "${DB_PASSWORD}" > ${POSTGRES_PASSWORD_FILE}

./compose ${DEPLOY}
docker-compose build --pull
