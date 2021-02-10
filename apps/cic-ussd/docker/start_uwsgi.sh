#!/bin/bash

. /root/db.sh

echo "pooooort $SERVER_PORT"
/usr/local/bin/uwsgi --wsgi-file /usr/local/lib/python3.8/site-packages/cic_ussd/runnable/server.py --http :$SERVER_PORT --pyargv "-vv"
