#!/bin/bash

. /root/db.sh

user_ussd_server_port=${SERVER_PORT:-9000}

/usr/local/bin/uwsgi --ini ./docker/uwsgi.ini --wsgi-file cic_ussd/runnable/daemons/cic_user_ussd_server.py --stats 0.0.0.0:5050 --stats-http --http :"$user_ussd_server_port" --pyargv "$@"
