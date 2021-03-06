#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

set -e

if [ ! -z $DEV_FEE_PRICE ]; then
	gas_price_arg="--gas-price $DEV_FEE_PRICE"
	fee_price_arg="--fee-price $DEV_FEE_PRICE"
fi

must_eth_rpc

# Deploy address declarator registry
advance_nonce
debug_rpc
>&2 echo -e "\033[;96mDeploy address declarator contract\033[;39m"
DEV_ADDRESS_DECLARATOR=`eth-address-declarator-deploy --nonce $nonce -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG $DEV_DECLARATOR_DESCRIPTION`

check_wait 1

echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +a
set +e
