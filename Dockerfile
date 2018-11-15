FROM comses/base:latest

ARG DJANGO_RUNIT_SCRIPT=./deploy/runit/dev.sh
ARG UBUNTU_MIRROR=mirror.math.princeton.edu/pub

RUN sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
    && apt-get update && apt-get install -q -y \
    curl \
    git \
    libxml2-dev \
    postgresql-client \
    python3-dev \
    python3-pip \
    python3-setuptools \
    ssmtp \
    wget \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
    && mkdir -p /etc/service/django \
    && mkdir -p /etc/service/sockjs  \
    && touch /etc/service/django/run /etc/service/sockjs/run /etc/postgresql-backup-pre \
    && chmod a+x /etc/service/django/run /etc/service/sockjs/run /etc/postgresql-backup-pre \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ./deploy/db/postgresql-backup-pre /etc/
COPY ${DJANGO_RUNIT_SCRIPT} /etc/service/django/run
COPY ./deploy/runit/sockjs.sh /etc/service/sockjs/run

COPY deploy/mail/ssmtp.conf /etc/ssmtp/ssmtp.conf
# copy cron script to be run daily
COPY deploy/cron/daily_catalog_tasks /etc/cron.daily/
COPY deploy/cron/monthly_catalog_tasks /etc/cron.monthly/

WORKDIR /code
COPY requirements.txt /code/
# Set execute bit on the cron script and install pip dependencies
RUN pip3 install -r /code/requirements.txt

