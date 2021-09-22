#!/bin/bash

set -e
set -u

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-600}

. ./db.sh

if [ $? -ne "0" ]; then
	>&2 echo db migrate fail
	exit 1
fi

if [[ "$CONTRACT_MIGRATION_URL" ]]; then
  echo "waiting for $CONTRACT_MIGRATION_URL/readyz"
  ./wait-for-it.sh $CONTRACT_MIGRATION_URL  -t $WAIT_FOR_TIMEOUT 
  source ./get_readyz.sh # set env vars form endpoint
  /usr/local/bin/cic-cache-taskerd -vv
else
  /usr/local/bin/cic-cache-taskerd -vv
fi

