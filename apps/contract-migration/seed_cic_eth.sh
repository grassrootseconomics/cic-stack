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
DEV_TOKEN_TYPE=${DEV_TOKEN_TYPE:-giftable}
if [ $DEV_TOKEN_TYPE = 'giftable' ]; then
	token_symbol='GFT'
else
	token_symbol='SRF'
fi

# Debug flag
DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
keystore_file=./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c
debug='-vv'
abi_dir=${ETH_ABI_DIR:-/usr/local/share/cic/solidity/abi}
gas_amount=100000000000000000000000
token_amount=${gas_amount}
env_out_file=${CIC_DATA_DIR}/.env_seed
init_level_file=${CIC_DATA_DIR}/.init
truncate $env_out_file -s 0

set -e
set -a

#pip install --extra-index-url $DEV_PIP_EXTRA_INDEX_URL  eth-address-index==0.1.1a7

# get required addresses from registries
DEV_TOKEN_INDEX_ADDRESS=`eth-contract-registry-list -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_REGISTRY_ADDRESS -f brief TokenRegistry`
DEV_ACCOUNT_INDEX_ADDRESS=`eth-contract-registry-list -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_REGISTRY_ADDRESS -f brief AccountRegistry`
DEV_RESERVE_ADDRESS=`eth-token-index-list -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_TOKEN_INDEX_ADDRESS -f brief GFT`
cat <<EOF
Token registry: $DEV_TOKEN_INDEX_ADDRESS
Account reigstry: $DEV_ACCOUNT_INDEX_ADDRESS
Reserve address: $DEV_RESERVE_ADDRESS
EOF

>&2 echo "create account for gas gifter"
old_gas_provider=$DEV_ETH_ACCOUNT_GAS_PROVIDER
DEV_ETH_ACCOUNT_GAS_GIFTER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_GAS_GIFTER >> $env_out_file
cic-eth-tag -i $CIC_CHAIN_SPEC GAS_GIFTER $DEV_ETH_ACCOUNT_GAS_GIFTER


>&2 echo "create account for sarafu gifter"
DEV_ETH_ACCOUNT_SARAFU_GIFTER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_SARAFU_GIFTER=$DEV_ETH_ACCOUNT_SARAFU_GIFTER >> $env_out_file
cic-eth-tag -i $CIC_CHAIN_SPEC SARAFU_GIFTER $DEV_ETH_ACCOUNT_SARAFU_GIFTER

>&2 echo "create account for approval escrow owner"
DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=$DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER >> $env_out_file
cic-eth-tag -i $CIC_CHAIN_SPEC TRANSFER_AUTHORIZATION_OWNER $DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER 

#>&2 echo "create account for faucet owner"
#DEV_ETH_ACCOUNT_FAUCET_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
#echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_FAUCET_OWNER >> $env_out_file
#cic-eth-tag FAUCET_GIFTER $DEV_ETH_ACCOUNT_FAUCET_OWNER

>&2 echo "create account for accounts index writer"
DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER=$DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER >> $env_out_file
cic-eth-tag -i $CIC_CHAIN_SPEC ACCOUNT_REGISTRY_WRITER $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER
>&2 echo "add acccounts index writer account as writer on contract"
eth-accounts-index-writer -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ACCOUNT_INDEX_ADDRESS -ww $debug $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER

# Transfer gas to custodial gas provider adddress
>&2 echo gift gas to gas gifter
>&2 eth-gas --send -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_GAS_GIFTER $gas_amount

>&2 echo gift gas to sarafu token owner
>&2 eth-gas --send -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_SARAFU_GIFTER $gas_amount

>&2 echo gift gas to account index owner
>&2 eth-gas --send -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_ACCOUNT_REGISTRY_WRITER $gas_amount


# Send token to token creator
>&2 echo "gift tokens to sarafu owner"
>&2 giftable-token-gift -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_RESERVE_ADDRESS --recipient $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $token_amount

# Send token to token gifter
>&2 echo "gift tokens to keystore address"
>&2 giftable-token-gift -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_RESERVE_ADDRESS --recipient $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER -w $debug $token_amount

>&2 echo "set sarafu token to reserve token (temporarily while bancor contracts are not connected)"
echo DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS >> $env_out_file
export DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS

# Transfer tokens to gifter address
>&2 echo "transfer sarafu tokens to token gifter address"
>&2 eth-transfer -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_RESERVE_ADDRESS -w $debug $DEV_ETH_ACCOUNT_SARAFU_GIFTER ${token_amount:0:-1}

#echo -n 0 > $init_level_file

# Remove the SEND (8), QUEUE (16) and INIT (2) locks (or'ed), set by default at migration
cic-eth-ctl -i :: unlock INIT
cic-eth-ctl -i :: unlock SEND
cic-eth-ctl -i :: unlock QUEUE

set +a
set +e
