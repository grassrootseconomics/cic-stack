#! /bin/sh

set -u
set -e

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
  -r $CIC_REGISTRY_ADDRESS --token-symbol $TOKEN_SYMBOL -y $KEYSTORE_FILE_PATH $OUT_DIR > import_task_log.log & 

import_pid=$!
echo "import_balance pid: $import_pid" 

echo "importing accounts"

python cic_ussd/import_users.py -vv -c config --ussd-host $USER_USSD_HOST --ussd-port $USER_USSD_PORT --ussd-no-ssl out

echo "importing user meta data"
node cic_meta/import_meta.js $OUT_DIR $NUMBER_OF_USERS 

echo "import meta prefereneces"
node cic_meta/import_meta_preferences.js $OUT_DIR $NUMBER_OF_USERS 

echo "Running validation!"
python verify.py -v -c config -r $CIC_REGISTRY_ADDRESS -p $ETH_PROVIDER \
  --token-symbol $TOKEN_SYMBOL $OUT_DIR 

kill $import_pid
exit 0
