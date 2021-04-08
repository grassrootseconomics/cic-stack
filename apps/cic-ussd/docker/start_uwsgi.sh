#!/bin/bash

. /root/db.sh

server_port=${SERVER_PORT:-9000}

/usr/local/bin/uwsgi --wsgi-file /usr/local/lib/python3.8/site-packages/cic_ussd/runnable/server.py --http :$server_port --pyargv "$@"
