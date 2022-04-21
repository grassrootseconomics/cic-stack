ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-e8eb2ee2

RUN apt-get install libffi-dev -y

# set working directory
WORKDIR /usr/src

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

# copy all files into working directory.
COPY . .

# copy and install requirements
COPY requirements.txt ./
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

# install cic-notify
RUN python setup.py install

# copy scripts
COPY docker/*.sh ./
RUN chmod +x /usr/src/*.sh

COPY cic_notify/db/migrations/ /usr/local/share/cic-notify/alembic/

ENTRYPOINT []