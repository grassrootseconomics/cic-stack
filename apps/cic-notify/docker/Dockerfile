ARG DEV_DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DEV_DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e

#RUN pip install $pip_extra_index_url_flag cic-base[full_graph]==0.1.2a62
RUN apt-get install libffi-dev -y


ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net:8433
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

COPY requirements.txt .

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .
RUN python setup.py install

COPY docker/*.sh ./
RUN chmod +x /root/*.sh

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY .config/ /usr/local/etc/cic-notify/
COPY cic_notify/db/migrations/ /usr/local/share/cic-notify/alembic/


ENTRYPOINT []
