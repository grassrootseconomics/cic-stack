# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-55da5f4e as dev

#RUN pip install $pip_extra_index_url_flag cic-base[full_graph]==0.1.2a62

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
COPY requirements.txt .

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url https://pypi.org/simple  \
	  --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL \
    -r requirements.txt

COPY . .
RUN python setup.py install

COPY docker/*.sh .
RUN chmod +x *.sh 

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY .config/ /usr/local/etc/cic-notify/
COPY cic_notify/db/migrations/ /usr/local/share/cic-notify/alembic/


ENTRYPOINT []
