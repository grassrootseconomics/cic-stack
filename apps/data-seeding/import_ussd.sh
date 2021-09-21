#!/bin/bash

if [[ -d "$OUT_DIR" ]]
then
  echo "found existing IMPORT DIR cleaning up..."
  rm -rf "$OUT_DIR"
  mkdir -p "$OUT_DIR"
else
  echo "IMPORT DIR does not exist creating it."
  mkdir -p "$OUT_DIR"
fi

# using timeout because the timeout flag for celery inspect does not work
timeout 5 celery inspect ping -b "$CELERY_BROKER_URL"
if [[ $? -eq 124 ]]
then
  >&2 echo "Celery workers not available. Is the CELERY_BROKER_URL ($CELERY_BROKER_URL) correct?"
  exit 1
fi

echo "Creating seed data..."
python create_import_users.py -vv  -c "$CONFIG" --dir "$OUT_DIR" "$NUMBER_OF_USERS"
wait $!

echo "Check for running celery workers ..."
if [ -f ./cic-ussd-import.pid ];
then
  echo "Found a running worker. Killing ..."
  kill -9 $(<cic-ussd-import.pid)
fi

echo "Purge tasks from celery worker"
celery -A cic_ussd.import_task purge -Q "$CELERY_QUEUE" --broker redis://"$REDIS_HOST":"$REDIS_PORT" -f

echo "Start celery work and import balance job"
if [ "$INCLUDE_BALANCES" != "y" ]
then
  echo "Running worker without opening balance transactions"
  TARGET_TX_COUNT=$NUMBER_OF_USERS
  nohup python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$OUT_DIR" > nohup.out 2> nohup.err < /dev/null &
else
  echo "Running worker with opening balance transactions"
  TARGET_TX_COUNT=$((NUMBER_OF_USERS*2))
  nohup python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --include-balances --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$OUT_DIR" &
fi

echo "Target count set to ${TARGET_TX_COUNT}"
until [ -f ./cic-import-ussd.pid ]
do
  echo "Polling for celery worker pid file..."
  sleep 1
done
IMPORT_BALANCE_JOB=$(<cic-import-ussd.pid)

echo "Start import users job"
if [ "$USSD_SSL" == "y" ]
then
  echo "Targeting secure ussd-user server"
  python cic_ussd/import_users.py -vv -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" "$OUT_DIR"
else
  python cic_ussd/import_users.py -vv -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" --ussd-no-ssl "$OUT_DIR"
fi

echo "Waiting for import balance job to complete ..."
tail --pid="$IMPORT_BALANCE_JOB" -f /dev/null
set -e

echo "Importing pins"
python cic_ussd/import_pins.py -c "$CONFIG" -vv "$OUT_DIR"
set +e
wait $!
set -e

echo "Importing ussd data"
python cic_ussd/import_ussd_data.py -c "$CONFIG" -vv "$OUT_DIR"
set +e
wait $!

echo "Importing person metadata"
node cic_meta/import_meta.js "$OUT_DIR" "$NUMBER_OF_USERS"

echo "Import preferences metadata"
node cic_meta/import_meta_preferences.js "$OUT_DIR" "$NUMBER_OF_USERS"

CIC_NOTIFY_DATABASE=postgres://$DATABASE_USER:$DATABASE_PASSWORD@$DATABASE_HOST:$DATABASE_PORT/$NOTIFY_DATABASE_NAME
NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
while [[ "$NOTIFICATION_COUNT" < "$TARGET_TX_COUNT" ]]
do
  NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
  sleep 5
  echo "Notification count is: ${NOTIFICATION_COUNT} of ${TARGET_TX_COUNT}. Checking after 5 ..."
done
echo "Running verify script."
python verify.py -c "$CONFIG" -v -p "$ETH_PROVIDER"  -r "$CIC_REGISTRY_ADDRESS" --exclude "$EXCLUSIONS" --meta-provider "$META_URL" --token-symbol "$TOKEN_SYMBOL" --ussd-provider "$USSD_PROVIDER" "$OUT_DIR"
