#! /bin/bash 
set -e
set -u
env
WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-600}

if [[ "$CONTRACT_MIGRATION_URL" ]]; then
  echo "waiting for $CONTRACT_MIGRATION_URL/readyz"
  ./scripts/wait-for-it.sh $CONTRACT_MIGRATION_URL  -t $WAIT_FOR_TIMEOUT 
  source ./scripts/get_readyz.sh # set env vars form endpoint
  ./import_ussd.sh
else
  ./import_ussd.sh
fi

