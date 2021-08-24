#!/bin/bash

# defaults
#initlevel=`cat ${CIC_DATA_DIR}/.init`
#echo $inilevel
#if [ $initlevel -lt 2 ]; then
#	>&2 echo "initlevel too low $initlevel"
#	exit 1 
#fi
source ${CIC_DATA_DIR}/.env
source ${CIC_DATA_DIR}/.env_all
DEV_PIP_EXTRA_INDEX_URL=${DEV_PIP_EXTRA_INDEX_URL:-https://pip.grassrootseconomics.net:8433}
DEV_DATABASE_NAME_CIC_ETH=${DEV_DATABASE_NAME_CIC_ETH:-"cic-eth"}
CIC_DATA_DIR=${CIC_DATA_DIR:-/tmp/cic} 
ETH_PASSPHRASE=''
CIC_DEFAULT_TOKEN_SYMBOL=${CIC_DEFAULT_TOKEN_SYMBOL:-GFT}
TOKEN_SYMBOL=$CIC_DEFAULT_TOKEN_SYMBOL

CHAIN_SPEC=${CHAIN_SPEC:-$CIC_CHAIN_SPEC}
RPC_HTTP_PROVIDER=${RPC_HTTP_PROVIDER:-$ETH_PROVIDER}

# Debug flag
DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
keystore_file=./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c
debug='-vv'
gas_amount=100000000000000000000000
token_amount=${gas_amount}
env_out_file=${CIC_DATA_DIR}/.env_seed
init_level_file=${CIC_DATA_DIR}/.init
empty_config_dir=$CONFINI_DIR/empty
truncate $env_out_file -s 0

set -e
set -a

#pip install --extra-index-url $DEV_PIP_EXTRA_INDEX_URL  eth-address-index==0.1.1a7

export CONFINI_DIR=$_CONFINI_DIR
unset CONFINI_DIR

# get required addresses from registries
DEV_TOKEN_INDEX_ADDRESS=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $ETH_PROVIDER -e $CIC_REGISTRY_ADDRESS -vv --raw TokenRegistry`
DEV_ACCOUNT_INDEX_ADDRESS=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $ETH_PROVIDER -e $CIC_REGISTRY_ADDRESS -vv --raw AccountRegistry`
DEV_RESERVE_ADDRESS=`eth-token-index-list -i $CHAIN_SPEC -u -p $ETH_PROVIDER -e $DEV_TOKEN_INDEX_ADDRESS -vv --raw $CIC_DEFAULT_TOKEN_SYMBOL`
cat <<EOF
Token registry: $DEV_TOKEN_INDEX_ADDRESS
Account reigstry: $DEV_ACCOUNT_INDEX_ADDRESS
Reserve address: $DEV_RESERVE_ADDRESS ($CIC_DEFAULT_TOKEN_SYMBOL)
EOF

>&2 echo "create account for gas gifter"
old_gas_provider=$DEV_ETH_ACCOUNT_GAS_PROVIDER
DEV_ETH_ACCOUNT_GAS_GIFTER=`CONFINI_DIR=$empty_config_dir cic-eth-create --redis-timeout 120 $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_GAS_GIFTER >> $env_out_file
cic-eth-tag -i $CHAIN_SPEC GAS_GIFTER $DEV_ETH_ACCOUNT_GAS_GIFTER


>&2 echo "create account for sarafu gifter"
DEV_ETH_ACCOUNT_SARAFU_GIFTER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_SARAFU_GIFTER=$DEV_ETH_ACCOUNT_SARAFU_GIFTER >> $env_out_file
cic-eth-tag -i $CHAIN_SPEC SARAFU_GIFTER $DEV_ETH_ACCOUNT_SARAFU_GIFTER

>&2 echo "create account for approval escrow owner"
DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=$DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER >> $env_out_file
cic-eth-tag -i $CHAIN_SPEC TRANSFER_AUTHORIZATION_OWNER $DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER 

#>&2 echo "create account for faucet owner"
#DEV_ETH_ACCOUNT_FAUCET_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
#echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_FAUCET_OWNER >> $env_out_file
#cic-eth-tag FAUCET_GIFTER $DEV_ETH_ACCOUNT_FAUCET_OWNER

>&2 echo "create account for accounts index writer"
DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=`CONFINI_DIR=$empty_config_dir cic-eth-create $debug --redis-host $REDIS_HOST --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=$DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER >> $env_out_file
cic-eth-tag -i $CHAIN_SPEC ACCOUNT_REGISTRY_WRITER $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER
>&2 echo "add acccounts index writer account as writer on contract"
eth-accounts-index-writer -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -e $DEV_ACCOUNT_INDEX_ADDRESS -ww $debug $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER

# Transfer gas to custodial gas provider adddress
_CONFINI_DIR=$CONFINI_DIR
unset CONFINI_DIR
>&2 echo gift gas to gas gifter
>&2 eth-gas -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_GAS_GIFTER $gas_amount

>&2 echo gift gas to sarafu token owner
>&2 eth-gas -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER $gas_amount

>&2 echo gift gas to account index owner
>&2 eth-gas -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -w $debug -a $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER $gas_amount


# Send token to token creator
>&2 echo "gift tokens to sarafu owner"
echo "giftable-token-gift -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -e $DEV_RESERVE_ADDRESS -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $token_amount"
>&2 giftable-token-gift -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -e $DEV_RESERVE_ADDRESS -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $token_amount

# Send token to token gifter
>&2 echo "gift tokens to keystore address"
>&2 giftable-token-gift -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER -e $DEV_RESERVE_ADDRESS -a $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER -w $debug $token_amount

>&2 echo "set sarafu token to reserve token (temporarily while bancor contracts are not connected)"
echo DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS >> $env_out_file
export DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS

# Transfer tokens to gifter address
>&2 echo "transfer tokens to token gifter address"
>&2 erc20-transfer -s -u -y $keystore_file -i $CHAIN_SPEC -p $ETH_PROVIDER --fee-limit 100000 -e $DEV_RESERVE_ADDRESS -w $debug -a $DEV_ETH_ACCOUNT_SARAFU_GIFTER ${token_amount:0:-1}

#echo -n 0 > $init_level_file

#CONFINI_DIR=$_CONFINI_DIR
# Remove the SEND (8), QUEUE (16) and INIT (2) locks (or'ed), set by default at migration
cic-eth-ctl -i $CHAIN_SPEC unlock INIT
cic-eth-ctl -i $CHAIN_SPEC unlock SEND
cic-eth-ctl -i $CHAIN_SPEC unlock QUEUE

export CONFINI_DIR=$_CONFINI_DIR

set +a
set +e
