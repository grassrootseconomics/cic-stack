#!/bin/bash

. /root/db.sh

user_server_port=${SERVER_PORT:-9500}

/usr/local/bin/uwsgi --wsgi-file cic_ussd/runnable/daemons/cic_user_server.py --http :"$user_server_port" --pyargv "$@"
