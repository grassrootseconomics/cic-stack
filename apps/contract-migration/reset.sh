#!/bin/bash

set -a

DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
DEV_ETH_ACCOUNT_RESERVE_MINTER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_ETH_RESERVE_AMOUNT=${DEV_ETH_RESERVE_AMOUNT:-""10000000000000000000000000000000000}
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

	DEV_ETH_RESERVE_ADDRESS=`giftable-token-deploy -p $ETH_PROVIDER -y $keystore_file -i $CIC_CHAIN_SPEC --account $DEV_ETH_ACCOUNT_RESERVE_MINTER --minter $DEV_ETH_ACCOUNT_RESERVE_MINTER --minter $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER -v -w --name "Sarafu" --symbol "SRF" --decimals 6 $DEV_ETH_RESERVE_AMOUNT`

	#BANCOR_REGISTRY_ADDRESS=`cic-bancor-deploy --bancor-dir /usr/local/share/cic/bancor -z $DEV_ETH_RESERVE_ADDRESS -p $ETH_PROVIDER -o $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`

	CIC_ACCOUNTS_INDEX_ADDRESS=`eth-accounts-index-deploy -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -y $keystore_file --writer $DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER -vv -w`

	CIC_REGISTRY_ADDRESS=`cic-registry-deploy -i $CIC_CHAIN_SPEC -y $keystore_file -k CICRegistry -k BancorRegistry -k AccountRegistry -k TokenRegistry -k AddressDeclarator -k Faucet -k TransferAuthorization -p $ETH_PROVIDER -vv -w`
	cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -k CICRegistry  -p $ETH_PROVIDER $CIC_REGISTRY_ADDRESS -vv
	#cic-registry-set -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -k BancorRegistry -p $ETH_PROVIDER $BANCOR_REGISTRY_ADDRESS -vv
	cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -k AccountRegistry -p $ETH_PROVIDER $CIC_ACCOUNTS_INDEX_ADDRESS  -vv

	# Deploy address declarator registry
	>&2 echo "deploy address declarator contract"
	declarator_description=0x546869732069732074686520434943206e6574776f726b000000000000000000
	CIC_DECLARATOR_ADDRESS=`eth-address-declarator-deploy -y $keystore_file -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -v $declarator_description`
	cic-registry-set -y $keystore_file -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -k AddressDeclarator -p $ETH_PROVIDER $CIC_DECLARATOR_ADDRESS  -vv

else
	echo "\$ETH_PROVIDER not set!"
	exit 1
fi

mkdir -p $CIC_DATA_DIR

# this is consumed in downstream services to set environment variables
cat << EOF > $CIC_DATA_DIR/.env
export DEV_ETH_RESERVE_ADDRESS=$DEV_ETH_RESERVE_ADDRESS
export DEV_ETH_RESERVE_AMOUNT=$DEV_ETH_RESERVE_AMOUNT
export DEV_ETH_ACCOUNTS_INDEX_ADDRESS=$CIC_ACCOUNTS_INDEX_ADDRESS
export BANCOR_REGISTRY_ADDRESS=$BANCOR_REGISTRY_ADDRESS
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
