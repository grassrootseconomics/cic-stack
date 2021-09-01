#!/usr/bin/env bash

set -e

echo "Creating seed data..."
python create_import_users.py -vv --dir "$IMPORT_DIR" "$ACCOUNT_COUNT"
wait $!
echo "Purge tasks from celery worker"
celery -A cic_ussd.import_task purge -Q "$CELERY_QUEUE" --broker redis://"$REDIS_HOST":"$REDIS_PORT" -f
echo "Start celery work and import balance job"
if [ "$INCLUDE_BALANCES" != "y" ]
then
  echo "Running worker without opening balance transactions"
  TARGET_TX_COUNT=$ACCOUNT_COUNT
  python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$IMPORT_DIR" &
else
  echo "Running worker with opening balance transactions"
  TARGET_TX_COUNT=$((ACCOUNT_COUNT*2))
  python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --include-balances --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$IMPORT_DIR" &
fi

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
  python cic_ussd/import_users.py -vv -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" "$IMPORT_DIR"
else
  python cic_ussd/import_users.py -vv -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" --ussd-no-ssl "$IMPORT_DIR"
fi
echo "Waiting for import balance job to complete ..."
tail --pid="$IMPORT_BALANCE_JOB" -f /dev/null
set -e
echo "Importing pins"
python cic_ussd/import_pins.py -c "$CONFIG" -vv "$IMPORT_DIR"
set +e
wait $!
set -e
echo "Importing ussd data"
python cic_ussd/import_ussd_data.py -c "$CONFIG" -vv "$IMPORT_DIR"
set +e
wait $!
echo "Importing person metadata"
node cic_meta/import_meta.js "$IMPORT_DIR" "$ACCOUNT_COUNT"
echo "Import preferences metadata"
node cic_meta/import_meta_preferences.js "$IMPORT_DIR" "$ACCOUNT_COUNT"
CIC_NOTIFY_DATABASE=postgres://$DATABASE_USER:$DATABASE_PASSWORD@$DATABASE_HOST:$DATABASE_PORT/$NOTIFY_DATABASE_NAME
NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
while [[ "$NOTIFICATION_COUNT" < "$TARGET_TX_COUNT" ]]
do
  NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
  sleep 5
  echo "Notification count is: ${NOTIFICATION_COUNT}. Checking after 5 ..."
done
python verify.py -c "$CONFIG" -v -p "$ETH_PROVIDER"  -r "$CIC_REGISTRY_ADDRESS" --exclude "$EXCLUSIONS" --token-symbol "$TOKEN_SYMBOL" "$IMPORT_DIR"
