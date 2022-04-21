#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}

set -e

if [ ! -z $DEV_FEE_PRICE ]; then
	gas_price_arg="--gas-price $DEV_FEE_PRICE"
	fee_price_arg="--fee-price $DEV_FEE_PRICE"
fi

must_address "$CIC_REGISTRY_ADDRESS" "registry"
must_eth_rpc


accounts_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw AccountRegistry`


>&2 echo -e "\033[;96mEnable default wallet $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER to write to accounts index contract at $accounts_index_address\033[;39m"
r=`eth-accounts-index-writer -s -w -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $accounts_index_address $DEV_DEBUG_FLAG $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`
add_pending_tx_hash $r
