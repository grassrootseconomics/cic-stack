FROM registry.gitlab.com/grassrootseconomics/cic-bancor:master-07951c84 

ARG pip_extra_index_url_flag='--extra-index-url https://pip.grassrootseconomics.net:8433'

RUN apk add postgresql-dev linux-headers git
# RUN apk add linux-headers

WORKDIR /usr/src

RUN mkdir -vp cic-cache

COPY requirements.txt cic-cache/
COPY setup.* cic-cache/
COPY cic_cache/ cic-cache/cic_cache/
COPY scripts/ cic-cache/scripts/
RUN cd cic-cache && \
	pip install $pip_extra_index_url_flag .

RUN cd cic-cache && \
	pip install .[server]

COPY tests/ cic-cache/tests/
#COPY db/ cic-cache/db
#RUN apk add postgresql-client

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY .config/ /usr/local/etc/cic-cache/

# for db migrations
RUN git clone https://github.com/vishnubob/wait-for-it.git /usr/local/bin/wait-for-it/
COPY cic_cache/db/migrations/ /usr/local/share/cic-cache/alembic/


# Tracker
# ENTRYPOINT ["/usr/local/bin/cic-cache-tracker", "-vv"]
# Server
# ENTRYPOINT [ "/usr/local/bin/uwsgi", "--wsgi-file", "/usr/local/lib/python3.8/site-packages/cic_cache/runnable/server.py", "--http", ":80", "--pyargv", "-vv" ]
