#!/bin/bash

# defaults
source ${DEV_DATA_DIR}/env_reset

# Debug flag
debug='-vv'
empty_config_dir=$CONFINI_DIR/empty

set -e
set -a

export CONFINI_DIR=$_CONFINI_DIR
unset CONFINI_DIR

# get required addresses from registries
token_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $ETH_PROVIDER -e $CIC_REGISTRY_ADDRESS -vv --raw TokenRegistry`
account_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $ETH_PROVIDER -e $CIC_REGISTRY_ADDRESS -vv --raw AccountRegistry`
reserve_address=`eth-token-index-list -i $CHAIN_SPEC -u -p $ETH_PROVIDER -e $token_index_address -vv --raw $CIC_DEFAULT_TOKEN_SYMBOL`

>&2 echo "Token registry: $token_index_address"
>&2 echo "Account registry: $account_index_address"
>&2 echo "Reserve address: $reserve_address ($TOKEN_SYMBOL)"

>&2 echo "create account for gas gifter"
old_gas_provider=$DEV_ETH_ACCOUNT_GAS_PROVIDER
#DEV_ETH_ACCOUNT_GAS_GIFTER=`CONFINI_DIR=$empty_config_dir cic-eth-create --redis-timeout 120 $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
DEV_ETH_ACCOUNT_GAS_GIFTER=`cic-eth-create --redis-timeout 120 $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
cic-eth-tag -i $CHAIN_SPEC GAS_GIFTER $DEV_ETH_ACCOUNT_GAS_GIFTER


>&2 echo "create account for sarafu gifter"
DEV_ETH_ACCOUNT_SARAFU_GIFTER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
cic-eth-tag -i $CHAIN_SPEC SARAFU_GIFTER $DEV_ETH_ACCOUNT_SARAFU_GIFTER

>&2 echo "create account for approval escrow owner"
DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
cic-eth-tag -i $CHAIN_SPEC TRANSFER_AUTHORIZATION_OWNER $DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER 

#>&2 echo "create account for faucet owner"
#DEV_ETH_ACCOUNT_FAUCET_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
#echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_FAUCET_OWNER >> $env_out_file
#cic-eth-tag FAUCET_GIFTER $DEV_ETH_ACCOUNT_FAUCET_OWNER

>&2 echo "create account for accounts index writer"
DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
#echo DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=$DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER >> $env_out_file
cic-eth-tag -i $CHAIN_SPEC ACCOUNT_REGISTRY_WRITER $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER
>&2 echo "add acccounts index writer account as writer on contract"
eth-accounts-index-writer -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -e $account_index_address -ww $debug $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER

# Transfer gas to custodial gas provider adddress
_CONFINI_DIR=$CONFINI_DIR
unset CONFINI_DIR
>&2 echo gift gas to gas gifter
>&2 eth-gas -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_GAS_GIFTER $DEV_GAS_AMOUNT

>&2 echo gift gas to sarafu token owner
>&2 eth-gas -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER $DEV_GAS_AMOUNT

>&2 echo gift gas to account index owner
>&2 eth-gas -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER $DEV_GAS_AMOUNT


# Send token to token creator
>&2 echo "gift tokens to sarafu owner"
echo "giftable-token-gift -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -e $reserve_address -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $DEV_TOKEN_AMOUNT"
>&2 giftable-token-gift -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -e $reserve_address -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $DEV_TOKEN_AMOUNT

# Send token to token gifter
>&2 echo "gift tokens to keystore address"
>&2 giftable-token-gift -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER -e $reserve_address -a $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER -w $debug $DEV_TOKEN_AMOUNT

>&2 echo "set sarafu token to reserve token (temporarily while bancor contracts are not connected)"
export DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS

# Transfer tokens to gifter address
>&2 echo "transfer tokens to token gifter address"
>&2 erc20-transfer -s -u -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $ETH_PROVIDER --fee-limit 100000 -e $reserve_address -w $debug -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER ${DEV_TOKEN_AMOUNT:0:-1}

#echo -n 0 > $init_level_file

#CONFINI_DIR=$_CONFINI_DIR
# Remove the SEND (8), QUEUE (16) and INIT (2) locks (or'ed), set by default at migration
cic-eth-ctl -i $CHAIN_SPEC unlock INIT
cic-eth-ctl -i $CHAIN_SPEC unlock SEND
cic-eth-ctl -i $CHAIN_SPEC unlock QUEUE

export CONFINI_DIR=$_CONFINI_DIR

set +a
set +e
