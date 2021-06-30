# syntax = docker/dockerfile:1.2
#FROM python:3.8.6-slim-buster as compile-image
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-5ab8bf45

RUN mkdir -vp /usr/local/etc/cic

COPY data-seeding/package.json \
     data-seeding/package-lock.json \
     .

RUN npm install

COPY data-seeding/requirements.txt . 

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
RUN pip install --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL -r requirements.txt 

COPY data-seeding/ . 

ENTRYPOINT [ ]
