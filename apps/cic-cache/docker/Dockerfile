FROM python:3.8.6-slim-buster

#COPY --from=0 /usr/local/share/cic/solidity/ /usr/local/share/cic/solidity/

WORKDIR /usr/src/cic-cache

ARG pip_extra_index_url_flag='--index https://pypi.org/simple --extra-index-url https://pip.grassrootseconomics.net:8433'
ARG root_requirement_file='requirements.txt'

#RUN apk update && \
#	apk add gcc musl-dev gnupg libpq
#RUN apk add postgresql-dev
#RUN apk add linux-headers
#RUN apk add libffi-dev
RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps git

# Copy shared requirements from top of mono-repo
RUN echo "copying root req file ${root_requirement_file}"
RUN pip install $pip_extra_index_url_flag cic-base[full_graph]==0.1.2a53

COPY cic-cache/requirements.txt ./
COPY cic-cache/setup.cfg \
	 cic-cache/setup.py \
 	 ./
COPY cic-cache/cic_cache/ ./cic_cache/
COPY cic-cache/scripts/ ./scripts/
COPY cic-cache/test_requirements.txt ./
RUN pip install $pip_extra_index_url_flag -r test_requirements.txt
RUN pip install $pip_extra_index_url_flag .
RUN pip install .[server]

COPY cic-cache/tests/ ./tests/
#COPY db/ cic-cache/db
#RUN apk add postgresql-client

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY cic-cache/config/ /usr/local/etc/cic-cache/

# for db migrations
RUN git clone https://github.com/vishnubob/wait-for-it.git /usr/local/bin/wait-for-it/
COPY cic-cache/cic_cache/db/migrations/ /usr/local/share/cic-cache/alembic/

RUN git clone https://gitlab.com/grassrootseconomics/cic-contracts.git && \
	mkdir -p /usr/local/share/cic/solidity && \
	cp -R cic-contracts/abis /usr/local/share/cic/solidity/abi

# Tracker
# ENTRYPOINT ["/usr/local/bin/cic-cache-tracker", "-vv"]
# Server
# ENTRYPOINT [ "/usr/local/bin/uwsgi", "--wsgi-file", "/usr/local/lib/python3.8/site-packages/cic_cache/runnable/server.py", "--http", ":80", "--pyargv", "-vv" ]
