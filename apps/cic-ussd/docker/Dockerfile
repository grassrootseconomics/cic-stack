ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e

RUN apt-get install -y redis-server
# create secrets directory
RUN mkdir -vp pgp/keys

# create application directory
RUN mkdir -vp cic-ussd
RUN mkdir -vp data

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net:8433
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
        cic-eth-aux-erc20-demurrage-token~=0.0.2a7


COPY *requirements.txt ./
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt 


COPY . .
RUN python setup.py install

COPY cic_ussd/db/ussd_menu.json data/

COPY docker/*.sh ./
RUN chmod +x /root/*.sh

# copy config and migration files to definitive file so they can be referenced in path definitions for running scripts
COPY config/ /usr/local/etc/cic-ussd/
COPY cic_ussd/db/migrations/ /usr/local/share/cic-ussd/alembic

ENTRYPOINT []
