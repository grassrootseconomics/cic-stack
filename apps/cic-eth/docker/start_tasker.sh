#!/bin/bash

set -e
. ./db.sh

# set CONFINI_ENV_PREFIX to override the env prefix to override env vars

echo "!!! starting signer"
python /usr/local/bin/crypto-dev-daemon -c /usr/local/etc/crypto-dev-signer &

echo "!!! starting tracker"
/usr/local/bin/cic-eth-taskerd $@

# thanks! https://docs.docker.com/config/containers/multi-service_container/
sleep 1;
echo "!!! entering monitor loop"
while true; do
  ps aux | grep crypto-dev-daemon | grep -q -v grep
  PROCESS_1_STATUS=$?
  ps aux | grep cic-eth-tasker |grep -q -v grep
  PROCESS_2_STATUS=$?
  # If the greps above find anything, they exit with 0 status
  # If they are not both 0, then something is wrong
  if [ $PROCESS_1_STATUS -ne 0 -o $PROCESS_2_STATUS -ne 0 ]; then
    echo "One of the processes has already exited."
    exit 1
  fi
  sleep 15;
done

set +e
