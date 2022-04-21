ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-e8eb2ee2

COPY requirements.txt .

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt


COPY . .
RUN pip install .  --extra-index-url $EXTRA_PIP_INDEX_URL

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
