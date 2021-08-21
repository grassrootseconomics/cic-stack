# syntax = docker/dockerfile:1.2
#FROM node:15.3.0-alpine3.10
FROM node:lts-alpine3.14

WORKDIR /root

RUN apk add --no-cache postgresql bash

# copy the dependencies
COPY package.json package-lock.json .
RUN --mount=type=cache,mode=0755,target=/root/.npm \
    npm set cache /root/.npm && \
    npm ci

COPY webpack.config.js .
COPY tsconfig.json . 
## required to build the cic-client-meta module
COPY src/ src/
COPY scripts/ scripts/
COPY tests/ tests/
COPY tests/*.asc /root/pgp/

## copy runtime configs
COPY .config/ /usr/local/etc/cic-meta/
#
## db migrations
COPY docker/db.sh ./db.sh
RUN chmod 755 ./db.sh
#

EXPOSE 8000

RUN alias tsc=node_modules/typescript/bin/tsc 
COPY docker/start_server.sh ./start_server.sh
RUN chmod 755 ./start_server.sh
ENTRYPOINT ["sh", "./start_server.sh"]
