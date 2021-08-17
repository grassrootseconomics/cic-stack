# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-55da5f4e as dev
RUN apt-get install -y redis-server
# create secrets directory
RUN mkdir -vp pgp/keys

# create application directory
RUN mkdir -vp cic-ussd
RUN mkdir -vp data

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
COPY requirements.txt .

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url https://pypi.org/simple  \
	  --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL \
    -r requirements.txt

COPY . .
RUN python setup.py install

COPY cic_ussd/db/ussd_menu.json data/

COPY docker/*.sh .
RUN chmod +x /root/*.sh

# copy config and migration files to definitive file so they can be referenced in path definitions for running scripts
COPY config/ /usr/local/etc/cic-ussd/
COPY cic_ussd/db/migrations/ /usr/local/share/cic-ussd/alembic

ENTRYPOINT []
