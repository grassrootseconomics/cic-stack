FROM python:3.8.5-alpine

# set working directory
WORKDIR /usr/src

# add args for installing from self-hosted packages
ARG pip_extra_index_url_flag='--extra-index-url https://pip.grassrootseconomics.net:8433'

# add alpine sys packages
RUN apk update && \
        apk add git linux-headers postgresql-dev gnupg bash
RUN apk add --update musl-dev gcc libffi-dev

# create application directory
RUN mkdir -vp cic-ussd

# copy all necessary files
COPY *requirements.txt cic-ussd/
COPY setup.* cic-ussd/
COPY cic_ussd/ cic-ussd/cic_ussd/
COPY scripts/ cic-ussd/scripts/
COPY states/ cic-ussd/states/
COPY transitions/ cic-ussd/transitions/
COPY var/ cic-ussd/var/
COPY docker/*.sh /root/

RUN chmod +x /root/*.sh

# install requirements
RUN cd cic-ussd && \
        pip install -r requirements.txt $pip_extra_index_url_flag

# copy config and migration files to definitive file so they can be referenced in path definitions for running scripts
COPY .config/ /usr/local/etc/cic-ussd/
COPY cic_ussd/db/migrations/ /usr/local/share/cic-ussd/alembic
