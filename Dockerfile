FROM comses/base:latest

ARG DJANGO_RUNIT_SCRIPT=./deploy/runit/dev.sh
ARG UBUNTU_MIRROR=mirror.math.princeton.edu/pub
ARG REQUIREMENTS_FILE=requirements-dev.txt

RUN sed -i "s|archive.ubuntu.com|${UBUNTU_MIRROR}|" /etc/apt/sources.list \
    && apt-get update && apt-get install -q -y \
    autopostgresqlbackup \
    curl \
    git \
    libxml2-dev \
    postgresql-client \
    python3-dev \
    python3-pip \
    python3-setuptools \
    postfix \
    wget \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1000 \
    && mkdir -p /etc/service/django \
    && mkdir -p /etc/service/sockjs  \
    && touch /etc/service/django/run /etc/service/sockjs/run /etc/postgresql-backup-pre \
    && chmod a+x /etc/service/django/run /etc/service/sockjs/run /etc/postgresql-backup-pre \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /code
COPY requirements*.txt /tmp/
# Set execute bit on the cron script and install pip dependencies
RUN pip3 install -r /tmp/${REQUIREMENTS_FILE}

COPY ./deploy/db/autopostgresqlbackup.conf /etc/default/autopostgresqlbackup
COPY ./deploy/db/postgresql-backup-pre /etc/
COPY ./deploy/db/autopostgresqlbackup /etc/cron.daily/
COPY ${DJANGO_RUNIT_SCRIPT} /etc/service/django/run
COPY ./deploy/runit/sockjs.sh /etc/service/sockjs/run
COPY deploy/mail/main.cf /etc/postfix/main.cf
COPY vcweb /code/vcweb
COPY tasks.py /code
