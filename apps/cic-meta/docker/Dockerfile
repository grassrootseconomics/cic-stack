FROM node:15.3.0-alpine3.10

WORKDIR /tmp/src/cic-meta

COPY cic-meta/package.json \
	 cic-meta/package-lock.json \
     ./

RUN npm install

COPY cic-meta/src/ src/
COPY cic-meta/tests/ tests/
COPY cic-meta/scripts/ scripts/
#COPY docker/*.sh /root/

RUN alias tsc=node_modules/typescript/bin/tsc 

COPY cic-meta/.config/ /usr/local/etc/cic-meta/
COPY cic-meta/scripts/server/initdb/server.postgres.sql /usr/local/share/cic-meta/sql/server.sql

COPY cic-meta/docker/db.sh ./db.sh
RUN chmod 755 ./db.sh

RUN alias ts-node=/tmp/src/cic-meta/node_modules/ts-node/dist/bin.js
ENTRYPOINT [ "./node_modules/ts-node/dist/bin.js", "./scripts/server/server.ts" ]

# COPY cic-meta/docker/start_server.sh ./start_server.sh
# RUN chmod 755 ./start_server.sh
