# FROM python:3.8.5-alpine
FROM python:3.8.6-slim-buster

# set working directory
WORKDIR /usr/src

# add args for installing from self-hosted packages
ARG pip_extra_index_url_flag='--extra-index-url https://pip.grassrootseconomics.net:8433'

RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps git python-pycurl

# create secrets directory
RUN mkdir -vp pgp/keys

# create application directory
RUN mkdir -vp cic-ussd
RUN mkdir -vp data

COPY cic-ussd/setup.cfg \
     cic-ussd/setup.py \
     cic-ussd/

COPY cic-ussd/requirements.txt \
     cic-ussd/test_requirements.txt \
     cic-ussd/

# install requirements
RUN cd cic-ussd && \
    pip install -r requirements.txt $pip_extra_index_url_flag

# copy all necessary files
COPY cic-ussd/cic_ussd/ cic-ussd/cic_ussd/
COPY cic-ussd/cic_ussd/db/ussd_menu.json data/
COPY cic-ussd/scripts/ cic-ussd/scripts/
COPY cic-ussd/states/ cic-ussd/states/
COPY cic-ussd/transitions/ cic-ussd/transitions/
COPY cic-ussd/var/ cic-ussd/var/

COPY cic-ussd/docker/db.sh \
     cic-ussd/docker/start_tasker.sh \
     cic-ussd/docker/start_uwsgi.sh \
     /root/

RUN chmod +x /root/*.sh
RUN cd cic-ussd && \
    pip install $pip_extra_index_url_flag .


# copy config and migration files to definitive file so they can be referenced in path definitions for running scripts
COPY cic-ussd/.config/ /usr/local/etc/cic-ussd/
COPY cic-ussd/cic_ussd/db/migrations/ /usr/local/share/cic-ussd/alembic

WORKDIR /root