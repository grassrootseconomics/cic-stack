#!/bin/bash

. /root/db.sh

user_ussd_server_port=${SERVER_PORT:-9000}

/usr/local/bin/uwsgi --wsgi-file /usr/local/lib/python3.8/site-packages/cic_ussd/runnable/daemons/cic_user_ussd_server.py --http :"$user_ussd_server_port" --pyargv "$@"
