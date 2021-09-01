# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-5ab8bf45

WORKDIR /root

RUN mkdir -vp /usr/local/etc/cic

COPY package.json \
     package-lock.json \
     .


RUN npm ci --production 
#RUN --mount=type=cache,mode=0755,target=/root/node_modules npm install

COPY requirements.txt . 

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip pip install \
    --extra-index-url $GITLAB_PYTHON_REGISTRY \
    --extra-index-url $EXTRA_INDEX_URL -r requirements.txt

COPY . . 

ENTRYPOINT [ ]
