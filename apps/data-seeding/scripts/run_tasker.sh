#! /bin/bash 

python cic_ussd/import_balance.py -v -c config -p $ETH_PROVIDER -r $CIC_REGISTRY_ADDRESS --token-symbol $TOKEN_SYMBOL -y $KEYSTORE_FILE_PATH $OUT_DIR
