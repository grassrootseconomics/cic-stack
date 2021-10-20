# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-5ab8bf45

WORKDIR /root

RUN mkdir -vp /usr/local/etc/cic

COPY package.json \
     package-lock.json \
     ./


RUN npm ci --production 
#RUN --mount=type=cache,mode=0755,target=/root/node_modules npm install

COPY common/ cic_ussd/common/
COPY requirements.txt .
COPY config/ config

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net:8433
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN  pip install --index-url $PIP_INDEX_URL  \
	  --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . . 

ENTRYPOINT [ ]
