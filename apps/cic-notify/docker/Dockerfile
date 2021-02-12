FROM python:3.8.6

RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps

WORKDIR /usr/src/cic-notify

ARG pip_extra_index_url_flag='--index https://pypi.org/simple --extra-index-url https://pip.grassrootseconomics.net:8433'
ARG root_requirement_file='requirements.txt'
RUN echo "copying root req file ${root_requirement_file}"
COPY $root_requirement_file .
RUN pip install -r $root_requirement_file $pip_extra_index_url_flag

COPY cic-notify/setup.cfg \
	 cic-notify/setup.py \
     ./

COPY cic-notify/cic_notify/ ./cic_notify/

COPY cic-notify/requirements.txt \
	 cic-notify/test_requirements.txt \
     ./

COPY cic-notify/scripts/ scripts/
RUN pip install $pip_extra_index_url_flag .[africastalking,notifylog]

COPY cic-notify/tests/ tests/
COPY cic-notify/docker/db.sh \
     cic-notify/docker/start_tasker.sh \
	 /root/

#RUN apk add postgresql-client
#RUN apk add bash

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY cic-notify/.config/ /usr/local/etc/cic-notify/
COPY cic-notify/cic_notify/db/migrations/ /usr/local/share/cic-notify/alembic/

WORKDIR /root
