#!/bin/bash

set -e
set -u

. ./db.sh

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-600}

if [[ "$CONTRACT_MIGRATION_URL" ]]; then
  echo "waiting for $CONTRACT_MIGRATION_URL/readyz"
  ./wait-for-it.sh $CONTRACT_MIGRATION_URL  -t $WAIT_FOR_TIMEOUT 
  source ./get_readyz.sh # set env vars form endpoint
  /usr/local/bin/cic-eth-dispatcherd $@
else
  /usr/local/bin/cic-eth-dispatcherd $@
fi
