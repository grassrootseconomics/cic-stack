#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

set -e

TOKEN_ADDRESS=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw DefaultToken --fee-limit 8000000`
if [ "$TOKEN_ADDRESS" == '0000000000000000000000000000000000000000' ]; then
	>&2 echo -e "\033[;33mFound no existing default token in token registry"
	exit 1
fi


TOKEN_SYMBOL=`erc20-info $DEV_DEBUG_FLAG -e $TOKEN_ADDRESS --fee-limit 1000000 --raw symbol`

>&2 echo -e "\033[;96mWriting immutable token proof for token $TOKEN_ADDRESS\033[;39m"
curl -X POST $META_URL -H 'Content-type: application/json' -H 'X-CIC-AUTOMERGE: immutable' --data-binary @${DEV_TOKEN_DATA_PATH}/proof.json

ptr=`cic-ptr -t token_meta $DEV_DEBUG_FLAG_FLAT $TOKEN_ADDRESS` 
>&2 echo -e "\033[;96mWriting 'token_meta' metadata pointer $ptr for token $TOKEN_SYMBOL ($TOKEN_ADDRESS)\033[;39m"
./meta.sh $ptr ${DEV_TOKEN_DATA_PATH}/meta.json

ptr=`cic-ptr -t token_meta_symbol $DEV_DEBUG_FLAG_FLAT $TOKEN_SYMBOL` 
>&2 echo -e "\033[;96mWriting 'token_meta_symbol' metadata pointer $ptr for token $TOKEN_SYMBOL ($TOKEN_ADDRESS)\033[;39m"
./meta.sh $ptr ${DEV_TOKEN_DATA_PATH}/meta.json

ptr=`cic-ptr -t token_proof $DEV_DEBUG_FLAG_FLAT $TOKEN_ADDRESS` 
>&2 echo -e "\033[;96mWriting 'token_proof' metadata pointer $ptr for token $TOKEN_SYMBOL ($TOKEN_ADDRESS)\033[;39m"
./meta.sh $ptr ${DEV_TOKEN_DATA_PATH}/proof.json

ptr=`cic-ptr -t token_proof_symbol $DEV_DEBUG_FLAG_FLAT $TOKEN_SYMBOL` 
>&2 echo -e "\033[;96mWriting 'token_meta' metadata pointer $ptr for token $TOKEN_SYMBOL ($TOKEN_ADDRESS)\033[;39m"
./meta.sh $ptr ${DEV_TOKEN_DATA_PATH}/proof.json

>&2 echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +e
set +a
