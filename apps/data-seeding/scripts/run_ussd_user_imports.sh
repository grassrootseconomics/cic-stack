#! /bin/bash

set -u
set -e

contract_migration_complete=0
retry_count=0
retry_sleep=30 #seconds
retry_limit="$((${TIMEOUT_MINUTES:-10}*60/2))"
while [[ $contract_migration_complete -ne 1 ]]
do
  if [[ -f "$CIC_DATA_DIR/.env"  ]] && grep -q CIC_DECLARATOR_ADDRESS $CIC_DATA_DIR/.env
  then
    echo "🤜💥🤛 data-seeding found the output of contract-migration!"
    source /tmp/cic/config/.env
    env
    contract_migration_complete=1
  elif [[ $retry_count -ge $retry_limit ]] 
  then
    echo "😢 data-seeding timeout waiting for contract migration to finish." >&2
    exit 1
  else
    echo "⏳ data-seeding waiting for contract-migration output $retry_count:$retry_limit ..."
    ((retry_count= $retry_count + $retry_sleep))
    sleep $retry_sleep 
  fi
done
  


while getopts ":n:o:g:" opt; do
  case $opt in
    n) NUMBER_OF_USERS="$OPTARG"
    ;;
    o) OUT_DIR="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

# using timeout because the timeout flag for celery inspect does not work
timeout 5 celery inspect ping -b $CELERY_BROKER_URL
if [[ $? -eq 124 ]] 
then
  >&2 echo "Celery workers not available. Is the CELERY_BROKER_URL ($CELERY_BROKER_URL) correct?"
  exit 1
fi

if [[ -d $OUT_DIR ]]
then
  echo "found existing OUT_DIR cleaning up..."
  rm -rf $OUT_DIR
  mkdir -p $OUT_DIR
else
  echo "OUT_DIR does not exist creating it."
  mkdir -p $OUT_DIR
fi


echo "creating accounts"

python create_import_users.py --dir $OUT_DIR $NUMBER_OF_USERS

echo "purging existing ussd tasks..."

celery -A cic_ussd.import_task purge -Q cic-import-ussd --broker $CELERY_BROKER_URL -f


echo "running import_balance in the background..."

python cic_ussd/import_balance.py -v -c config -p $ETH_PROVIDER \
  -r $CIC_REGISTRY_ADDRESS --token-symbol $TOKEN_SYMBOL -y $KEYSTORE_FILE_PATH $OUT_DIR 2>&1 & 

echo "import_balance pid: $!" 

echo "importing accounts"

python cic_ussd/import_users.py -vv -c config --ussd-host $USER_USSD_HOST --ussd-port $USER_USSD_PORT --ussd-no-ssl out
