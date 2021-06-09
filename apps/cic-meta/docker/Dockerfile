FROM node:15.3.0-alpine3.10

WORKDIR /tmp/src/cic-meta

RUN apk add --no-cache postgresql bash

# required to build the cic-client-meta module
COPY cic-meta/src/ src/
COPY cic-meta/scripts/ scripts/

# copy the dependencies
COPY cic-meta/package.json .
COPY cic-meta/tsconfig.json . 
COPY cic-meta/webpack.config.js .
     
RUN npm install

COPY cic-meta/tests/ tests/
COPY cic-meta/tests/*.asc /root/pgp/

# copy runtime configs
COPY cic-meta/.config/ /usr/local/etc/cic-meta/

# db migrations
COPY cic-meta/docker/db.sh ./db.sh
RUN chmod 755 ./db.sh

RUN alias tsc=node_modules/typescript/bin/tsc 
COPY cic-meta/docker/start_server.sh ./start_server.sh
RUN chmod 755 ./start_server.sh
ENTRYPOINT ["sh", "./start_server.sh"]
