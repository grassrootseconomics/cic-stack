#!/bin/bash

# defaults
initlevel=`cat ${CIC_DATA_DIR}/.init`
echo $inilevel
if [ $initlevel -lt 2 ]; then
	>&2 echo "initlevel too low $initlevel"
	exit 1 
fi
source ${CIC_DATA_DIR}/.env
source ${CIC_DATA_DIR}/.env_all
DEV_PIP_EXTRA_INDEX_URL=${DEV_PIP_EXTRA_INDEX_URL:-https://pip.grassrootseconomics.net:8433}
DEV_DATABASE_NAME_CIC_ETH=${DEV_DATABASE_NAME_CIC_ETH:-"cic-eth"}
CIC_DATA_DIR=${CIC_DATA_DIR:-/tmp/cic} 

# Debug flag
DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
keystore_file=./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c
debug='-vv'
abi_dir=${ETH_ABI_DIR:-/usr/local/share/cic/solidity/abi}
gas_amount=100000000000000000000000
token_amount=${gas_amount}
#faucet_amount=1000000000
faucet_amount=0
env_out_file=${CIC_DATA_DIR}/.env_seed
init_level_file=${CIC_DATA_DIR}/.init
truncate $env_out_file -s 0


set -e
set -a

# We need to not install these here...
pip install --extra-index-url $DEV_PIP_EXTRA_INDEX_URL cic-eth==0.10.0a34 chainlib==0.0.1a19 cic-contracts==0.0.2a2

>&2 echo "create account for gas gifter"
old_gas_provider=$DEV_ETH_ACCOUNT_GAS_PROVIDER
DEV_ETH_ACCOUNT_GAS_GIFTER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_GAS_GIFTER >> $env_out_file
cic-eth-tag GAS_GIFTER $DEV_ETH_ACCOUNT_GAS_GIFTER

>&2 echo "create account for sarafu gifter"
DEV_ETH_ACCOUNT_SARAFU_GIFTER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_SARAFU_GIFTER=$DEV_ETH_ACCOUNT_SARAFU_GIFTER >> $env_out_file
cic-eth-tag SARAFU_GIFTER $DEV_ETH_ACCOUNT_SARAFU_GIFTER

>&2 echo "create account for approval escrow owner"
DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER=$DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER >> $env_out_file
cic-eth-tag TRANSFER_AUTHORIZATION_OWNER $DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER 

#>&2 echo "create account for faucet owner"
#DEV_ETH_ACCOUNT_FAUCET_OWNER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
#echo DEV_ETH_ACCOUNT_GAS_GIFTER=$DEV_ETH_ACCOUNT_FAUCET_OWNER >> $env_out_file
#cic-eth-tag FAUCET_GIFTER $DEV_ETH_ACCOUNT_FAUCET_OWNER

>&2 echo "create account for accounts index writer"
DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=`cic-eth-create $debug --redis-host-callback=$REDIS_HOST --redis-port-callback=$REDIS_PORT --no-register`
echo DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=$DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER >> $env_out_file
cic-eth-tag ACCOUNTS_INDEX_WRITER $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER


# Transfer gas to custodial gas provider adddress
>&2 echo gift gas to gas gifter
>&2 eth-gas -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_GAS_GIFTER $gas_amount

>&2 echo gift gas to sarafu token owner
>&2 eth-gas -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_SARAFU_GIFTER $gas_amount

>&2 echo gift gas to account index owner
>&2 eth-gas -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER $gas_amount

# Send token to token creator
>&2 echo "gift tokens to sarafu owner"
>&2 giftable-token-gift -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ETH_RESERVE_ADDRESS --recipient $DEV_ETH_ACCOUNT_SARAFU_GIFTER -w $debug $token_amount

# Send token to token gifter
>&2 echo "gift tokens to keystore address"
>&2 giftable-token-gift -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ETH_RESERVE_ADDRESS --recipient $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER -w $debug $token_amount


>&2 echo "set sarafu token to reserve token (temporarily while bancor contracts are not connected)"
echo DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS >> $env_out_file
export DEV_ETH_SARAFU_TOKEN_ADDRESS=$DEV_ETH_RESERVE_ADDRESS

# Transfer tokens to gifter address
>&2 echo "transfer sarafu tokens to token gifter address"
>&2 eth-transfer -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --abi-dir $abi_dir -w $debug $DEV_ETH_ACCOUNT_SARAFU_GIFTER ${token_amount:0:-1}


>&2 echo "deploy transfer authorization contract"
#CIC_TRANSFER_AUTHORIZATION_ADDRESS=`erc20-approval-escrow-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --approver $DEV_ETH_ACCOUNT_TRANSFER_AUTHORIZATION_OWNER -w $debug`
#echo CIC_APPROVAL_ESCROW_ADDRESS=$CIC_TRANSFER_AUTHORIZATION_ADDRESS  >> $env_out_file
#export CIC_TRANSFER_AUTHORIZATION_ADDRESS=$CIC_TRANSFER_AUTHORIZATION_ADDRESS 

# Register transfer approval contract
#>&2 echo "add transfer approval request contract to registry"
#>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k TransferApproval -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $CIC_TRANSFER_AUTHORIZATION_ADDRESS


# Deploy one-time token faucet for newly created token
>&2 echo "deploy faucet"
DEV_ETH_SARAFU_FAUCET_ADDRESS=`sarafu-faucet-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --editor $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER --set-amount $faucet_amount --accounts-index-address $DEV_ETH_ACCOUNTS_INDEX_ADDRESS -w $debug`
echo DEV_ETH_SARAFU_FAUCET_ADDRESS=$DEV_ETH_SARAFU_FAUCET_ADDRESS  >> $env_out_file
export DEV_ETH_SARAFU_FAUCET_ADDRESS=$DEV_ETH_SARAFU_FAUCET_ADDRESS 

# Transfer tokens to faucet contract
>&2 echo "transfer tokens to faucet contract"
>&2 eth-transfer  -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS --abi-dir $abi_dir -w $debug $DEV_ETH_SARAFU_FAUCET_ADDRESS ${token_amount:0:-1}

# Register faucet entry
>&2 echo "register faucet contract in registry"
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k Faucet -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug $DEV_ETH_SARAFU_FAUCET_ADDRESS

>&2 echo "add faucet contract as token minter"
>&2 giftable-token-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug --token-address $DEV_ETH_SARAFU_TOKEN_ADDRESS $DEV_ETH_SARAFU_FAUCET_ADDRESS

>&2 echo "deploy token symbol index contract"
CIC_TOKEN_INDEX_ADDRESS=`eth-token-index-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w $debug`
echo CIC_TOKEN_INDEX_ADDRESS=$CIC_TOKEN_INDEX_ADDRESS >> $env_out_file
export CIC_TOKEN_INDEX_ADDRESS=$CIC_TOKEN_INDEX_ADDRESS
>&2 eth-token-index-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_TOKEN_INDEX_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS

# Register token registry
>&2 echo "register token index in registry"
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k TokenRegistry -i $CIC_CHAIN_SPEC -w -p $ETH_PROVIDER $CIC_TOKEN_INDEX_ADDRESS

>&2 echo "add declarations for sarafu token"
token_description_one=`sha256sum sarafu_declaration.json | awk '{ print $1; }'`
token_description_two=0x54686973206973207468652053617261667520746f6b656e0000000000000000
>&2 eth-address-declarator-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_DECLARATOR_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS $token_description_one
>&2 eth-address-declarator-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_DECLARATOR_ADDRESS -w $debug $DEV_ETH_SARAFU_TOKEN_ADDRESS $token_description_two


# Register address declarator
>&2 echo "add address declarator to registry"
>&2 cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -k AddressDeclarator -i $CIC_CHAIN_SPEC -w -p $ETH_PROVIDER $CIC_DECLARATOR_ADDRESS 

# We're done with the registry at this point, seal it off
>&2 echo "seal registry contract"
>&2 cic-registry-seal -y $keystore_file -i $CIC_CHAIN_SPEC -r $CIC_REGISTRY_ADDRESS -w -p $ETH_PROVIDER


# Add accounts index writer with key from keystore
>&2 echo "add keystore account $keystore_file to accounts index writers"
>&2 eth-accounts-index-add -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -r $CIC_ACCOUNTS_INDEX_ADDRESS --writer $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER -w $debug

echo -n 0 > $init_level_file

set +a
set +e
