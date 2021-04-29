#!/bin/bash

. ./db.sh

if [ $? -ne "0" ]; then
	>&2 echo db migrate fail
	exit 1
fi

/usr/local/bin/cic-cache-trackerd $@
