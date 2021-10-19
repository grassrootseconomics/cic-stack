#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}

set -e

if [ ! -z $DEV_ETH_GAS_PRICE ]; then
	gas_price_arg="--gas-price $DEV_ETH_GAS_PRICE"
	fee_price_arg="--fee-price $DEV_ETH_GAS_PRICE"
fi

must_address "$CIC_REGISTRY_ADDRESS" "registry"
must_eth_rpc

# get required addresses from registries
token_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw TokenRegistry`
accounts_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw AccountRegistry`
reserve_address=`eth-token-index-list -i $CHAIN_SPEC -u -p $RPC_PROVIDER -e $token_index_address $DEV_DEBUG_FLAG --raw $CIC_DEFAULT_TOKEN_SYMBOL`


REDIS_HOST_CALLBACK=${REDIS_HOST_CALLBACK:-$REDIS_HOST}
REDIS_PORT_CALLBACK=${REDIS_PORT_CALLBACK:-$REDIS_PORT}
>&2 echo -e "\033[;96mcreate account for gas gifter\033[;39m"
gas_gifter=`cic-eth-create --redis-timeout 120 $DEV_DEBUG_FLAG --redis-host-callback $REDIS_HOST_CALLBACK --redis-port-callback $REDIS_PORT_CALLBACK --no-register`
cic-eth-tag -i $CHAIN_SPEC GAS_GIFTER $gas_gifter

>&2 echo -e "\033[;96mcreate account for accounts index writer\033[;39m"
accounts_index_writer=`cic-eth-create --redis-timeout 120 $DEV_DEBUG_FLAG --redis-host-callback $REDIS_HOST_CALLBACK --redis-port-callback $REDIS_PORT_CALLBACK --no-register`
cic-eth-tag -i $CHAIN_SPEC ACCOUNT_REGISTRY_WRITER $accounts_index_writer


# Assign system writer for accounts index
>&2 echo -e "\033[;96mEnable accounts index writer $accounts_index_writer to write to accounts index contract at $accounts_index_address\033[;39m"
r=`eth-accounts-index-writer -s -w -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $accounts_index_address $DEV_DEBUG_FLAG $accounts_index_writer`
add_pending_tx_hash $r


# Transfer gas to custodial gas provider adddress
advance_nonce
>&2 echo -e "\033[;96mGift gas to gas gifter $gas_gifter\033[;39m"
r=`eth-gas -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG -a $gas_gifter $DEV_GAS_AMOUNT`
add_pending_tx_hash $r

>&2 echo -e "\033[;96mgift gas to accounts index owner $accounts_index_writer\033[;39m"
advance_nonce
# for now we are using the same key for both
DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER
r=`eth-gas -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG -a $accounts_index_writer $DEV_GAS_AMOUNT`
add_pending_tx_hash $r


# Remove the SEND (8), QUEUE (16) and INIT (2) locks (or'ed), set by default at migration
cic-eth-ctl -vv -i $CHAIN_SPEC unlock INIT
cic-eth-ctl -vv -i $CHAIN_SPEC unlock SEND
cic-eth-ctl -vv -i $CHAIN_SPEC unlock QUEUE

check_wait 4

>&2 echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +e
set +a
