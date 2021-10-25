#!/bin/bash

if [[ -d "$OUT_DIR" ]]
then
  echo -e "\033[;96mfound existing IMPORT DIR cleaning up...\033[;96m"
  rm -rf "$OUT_DIR"
  mkdir -p "$OUT_DIR"
else
  echo -e "\033[;96mIMPORT DIR does not exist creating it.\033[;96m"
  mkdir -p "$OUT_DIR"
fi

# using timeout because the timeout flag for celery inspect does not work
timeout 5 celery inspect ping -b "$CELERY_BROKER_URL"
if [[ $? -eq 124 ]]
then
  >&2 echo -e "\033[;96mCelery workers not available. Is the CELERY_BROKER_URL ($CELERY_BROKER_URL) correct?\033[;96m"
  exit 1
fi

echo -e "\033[;96mCreating seed data...\033[;96m"
python create_import_users.py -vv  -c "$CONFIG" --dir "$OUT_DIR" "$NUMBER_OF_USERS"
wait $!

echo -e "\033[;96mCheck for running celery workers ...\033[;96m"
if [ -f ./cic-ussd-import.pid ];
then
  echo -e "\033[;96mFound a running worker. Killing ...\033[;96m"
  kill -9 $(<cic-ussd-import.pid)
fi

echo -e "\033[;96mPurge tasks from celery worker\033[;96m"
celery -A cic_ussd.import_task purge -Q "$CELERY_QUEUE" --broker redis://"$REDIS_HOST":"$REDIS_PORT" -f

echo -e "\033[;96mStart celery work and import balance job\033[;96m"
if [ "$INCLUDE_BALANCES" != "y" ]
then
  echo -e "\033[;96mRunning worker without opening balance transactions\033[;96m"
  TARGET_TX_COUNT=$NUMBER_OF_USERS
  nohup python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$OUT_DIR" > nohup.out 2> nohup.err < /dev/null &
else
  echo -e "\033[;96mRunning worker with opening balance transactions\033[;96m"
  TARGET_TX_COUNT=$((NUMBER_OF_USERS*2))
  nohup python cic_ussd/import_balance.py -vv -c "$CONFIG" -p "$ETH_PROVIDER" -r "$CIC_REGISTRY_ADDRESS" --include-balances --token-symbol "$TOKEN_SYMBOL" -y "$KEYSTORE_PATH" "$OUT_DIR" &
fi

echo -e "\033[;96mTarget count set to ${TARGET_TX_COUNT}"
until [ -f ./cic-import-ussd.pid ]
do
  echo -e "\033[;96mPolling for celery worker pid file...\033[;96m"
  sleep 1
done
IMPORT_BALANCE_JOB=$(<cic-import-ussd.pid)

echo -e "\033[;96mStart import users job\033[;96m"
if [ "$USSD_SSL" == "y" ]
then
  echo -e "\033[;96mTargeting secure ussd-user server\033[;96m"
  python cic_ussd/import_users.py -vv -f -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" "$OUT_DIR"
else
  python cic_ussd/import_users.py -vv -f -c "$CONFIG" --ussd-host "$USSD_HOST" --ussd-port "$USSD_PORT" --ussd-no-ssl "$OUT_DIR"
fi

echo -e "\033[;96mWaiting for import balance job to complete ...\033[;96m"
tail --pid="$IMPORT_BALANCE_JOB" -f /dev/null
set -e

echo -e "\033[;96mImporting pins\033[;96m"
python cic_ussd/import_pins.py -c "$CONFIG" -vv "$OUT_DIR"
set +e
wait $!
set -e

echo -e "\033[;96mImporting ussd data\033[;96m"
python cic_ussd/import_ussd_data.py -c "$CONFIG" -vv "$OUT_DIR"
set +e
wait $!

echo -e "\033[;96mImporting person metadata\033[;96m"
node cic_meta/import_meta.js "$OUT_DIR" "$NUMBER_OF_USERS"

echo -e "\033[;96mImport preferences metadata\033[;96m"
node cic_meta/import_meta_preferences.js "$OUT_DIR" "$NUMBER_OF_USERS"

CIC_NOTIFY_DATABASE=postgres://$DATABASE_USER:$DATABASE_PASSWORD@$DATABASE_HOST:$DATABASE_PORT/$NOTIFY_DATABASE_NAME
NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
while (("$NOTIFICATION_COUNT" < "$TARGET_TX_COUNT" ))
do
  NOTIFICATION_COUNT=$(psql -qtA "$CIC_NOTIFY_DATABASE" -c 'SELECT COUNT(message) FROM notification WHERE message IS NOT NULL')
  sleep 5
  echo -e "\033[;96mNotification count is: ${NOTIFICATION_COUNT} of ${TARGET_TX_COUNT}. Checking after 5 ...\033[;96m"
done
echo -e "\033[;96mRunning verify script.\033[;96m"
python verify.py -v -p "$ETH_PROVIDER"  -r "$CIC_REGISTRY_ADDRESS" --exclude "$EXCLUSIONS" --meta-provider "$META_URL" --token-symbol "$TOKEN_SYMBOL" --ussd-provider "$USSD_PROVIDER" "$OUT_DIR"
