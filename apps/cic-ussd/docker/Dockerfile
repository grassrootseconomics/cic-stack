ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-e8eb2ee2

RUN apt-get install -y redis-server

# create secrets directory
RUN mkdir -vp pgp/keys


ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY *requirements.txt ./
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt


COPY . .
RUN python setup.py install

# create local files directory
RUN mkdir -vp cic_ussd/data/locale

COPY docker/*.sh ./
RUN chmod +x /root/*.sh

## copy config and migration files to definitive file so they can be referenced in path definitions for running scripts
COPY config/ /usr/local/etc/cic-ussd/
COPY cic_ussd/db/migrations/ /usr/local/share/cic-ussd/alembic

# uwsgi stats server http
EXPOSE 5050

ENTRYPOINT []
