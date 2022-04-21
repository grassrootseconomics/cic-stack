#!/bin/bash

. /root/db.sh

user_server_port=${SERVER_PORT:-9500}

/usr/local/bin/uwsgi --ini ./docker/uwsgi.ini --wsgi-file cic_ussd/runnable/daemons/cic_user_server.py --stats 0.0.0.0:5050 --stats-http --http :"$user_server_port" --pyargv "$@" 

