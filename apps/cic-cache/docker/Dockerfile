ARG DOCKER_REGISTRY=registry.gitlab.com/grassrootseconomics

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e

COPY requirements.txt .

ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"

RUN    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --force-reinstall \
    --no-cache \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . . 

RUN python setup.py install

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
#COPY config/ /usr/local/etc/cic-cache/

# for db migrations
COPY ./aux/wait-for-it/wait-for-it.sh ./
COPY cic_cache/db/migrations/ /usr/local/share/cic-cache/alembic/

COPY /docker/start_tracker.sh ./start_tracker.sh
COPY /docker/db.sh ./db.sh
RUN chmod 755 ./*.sh
# Tracker
# ENTRYPOINT ["/usr/local/bin/cic-cache-tracker", "-vv"]
# Server
# ENTRYPOINT [ "/usr/local/bin/uwsgi", "--wsgi-file", "/usr/local/lib/python3.8/site-packages/cic_cache/runnable/server.py", "--http", ":80", "--pyargv", "-vv" ]
ENTRYPOINT []
