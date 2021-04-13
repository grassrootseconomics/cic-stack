#!/bin/bash

set -a

DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
DEV_ETH_ACCOUNT_RESERVE_MINTER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_RESERVE_AMOUNT=${DEV_ETH_RESERVE_AMOUNT:-""10000000000000000000000000000000000}
faucet_amount=${DEV_FAUCET_AMOUNT:-0}
keystore_file=$(realpath ./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c)

echo "environment:"
printenv
echo \n

# This is a grassroots team convention for building the Bancor contracts using the bancor protocol repository truffle setup
# Running this in docker-internal dev container (built from Docker folder in this repo) will write a
# source-able env file to CIC_DATA_DIR. Services dependent on these contracts can mount this file OR 
# define these parameters at runtime
# pushd /usr/src

init_level_file=${CIC_DATA_DIR}/.init
if [ ! -f ${CIC_DATA_DIR}/.init ]; then
  echo "Creating .init file..."
  mkdir -p $CIC_DATA_DIR
  touch /tmp/cic/config/.init
#   touch $init_level_file
fi
echo -n 1 > $init_level_file

# Abort on any error (including if wait-for-it fails).
set -e

# Wait for the backend to be up, if we know where it is.
if [[ -n "${ETH_PROVIDER}" ]]; then
	echo "waiting for ${ETH_PROVIDER}..."
  	./wait-for-it.sh "${ETH_PROVIDER_HOST}:${ETH_PROVIDER_PORT}"

	DEV_RESERVE_ADDRESS=`giftable-token-deploy -p $ETH_PROVIDER -y $keystore_file -i $CIC_CHAIN_SPEC -v -w --name "Sarafu" --symbol "SRF" --decimals 6`
	giftable-token-gift -p $ETH_PROVIDER -y $keystore_file -i $CIC_CHAIN_SPEC -v -w -a $DEV_RESERVE_ADDRESS $DEV_RESERVE_AMOUNT

	#BANCOR_REGISTRY_ADDRESS=`cic-bancor-deploy --bancor-dir /usr/local/share/cic/bancor -z $DEV_ETH_RESERVE_ADDRESS -p $ETH_PROVIDER -o $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`

	>&2 echo "deploy account index contract"
	DEV_ACCOUNT_INDEX_ADDRESS=`eth-accounts-index-deploy -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -y $keystore_file -vv -w`
	>&2 echo "add deployer address as account index writer"
	eth-accounts-index-writer -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ACCOUNT_INDEX_ADDRESS -ww $debug $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER

	CIC_REGISTRY_ADDRESS=`eth-contract-registry-deploy -i $CIC_CHAIN_SPEC -y $keystore_file --identifier BancorRegistry --identifier AccountRegistry --identifier TokenRegistry --identifier AddressDeclarator --identifier Faucet --identifier TransferAuthorization -p $ETH_PROVIDER -vv -w`
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $ETH_PROVIDER -vv ContractRegistry $CIC_REGISTRY_ADDRESS
	#cic-registry-set -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -k BancorRegistry -p $ETH_PROVIDER $BANCOR_REGISTRY_ADDRESS -vv
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv AccountRegistry $DEV_ACCOUNT_INDEX_ADDRESS

	# Deploy address declarator registry
	>&2 echo "deploy address declarator contract"
	declarator_description=0x546869732069732074686520434943206e6574776f726b000000000000000000
	DEV_DECLARATOR_ADDRESS=`eth-address-declarator-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -v $declarator_description`
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv AddressDeclarator $DEV_DECLARATOR_ADDRESS

	# Deploy transfer authorization contact
	>&2 echo "deploy address declarator contract"
	DEV_TRANSFER_AUTHORIZATION_ADDRESS=`erc20-transfer-auth-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -v`
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $ETH_PROVIDER -vv TransferAuthorization $DEV_TRANSFER_AUTHORIZATION_ADDRESS

	# Deploy token index contract
	>&2 echo "deploy token index contract"
	DEV_TOKEN_INDEX_ADDRESS=`eth-token-index-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -v`
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv TokenRegistry $DEV_TOKEN_INDEX_ADDRESS 
	>&2 echo "add reserve token to token index"
	eth-token-index-add -w -y $keystore_file  -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv -a $DEV_TOKEN_INDEX_ADDRESS $DEV_RESERVE_ADDRESS

	# Sarafu faucet contract
	>&2 echo "deploy token faucet contract"
	DEV_FAUCET_ADDRESS=`sarafu-faucet-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -v --account-index-address $DEV_ACCOUNT_INDEX_ADDRESS $DEV_RESERVE_ADDRESS`
	eth-contract-registry-set -w -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv Faucet $DEV_FAUCET_ADDRESS
	>&2 echo "set faucet as token minter"
	giftable-token-minter -w -y $keystore_file -a $DEV_RESERVE_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv $DEV_FAUCET_ADDRESS

	>&2 echo "set token faucet amount"
	sarafu-faucet-set -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_FAUCET_ADDRESS $faucet_amount


else
	echo "\$ETH_PROVIDER not set!"
	exit 1
fi

mkdir -p $CIC_DATA_DIR

# this is consumed in downstream services to set environment variables
cat << EOF > $CIC_DATA_DIR/.env
export CIC_REGISTRY_ADDRESS=$CIC_REGISTRY_ADDRESS
export CIC_TRUST_ADDRESS=$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER
export CIC_DECLARATOR_ADDRESS=$CIC_DECLARATOR_ADDRESS
EOF

cat ./envlist | bash from_env.sh > $CIC_DATA_DIR/.env_all
# popd

set +a
set +e

echo -n 2 > $init_level_file

exec "$@"
