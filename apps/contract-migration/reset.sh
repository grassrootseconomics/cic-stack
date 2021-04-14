#!/bin/bash

set -a

CIC_CHAIN_SPEC=${CIC_CHAIN_SPEC:-evm:bloxberg:8995}
DEV_TOKEN_TYPE=${DEV_TOKEN_TYPE:-giftable}
DEV_ETH_ACCOUNT_RESERVE_MINTER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
DEV_RESERVE_AMOUNT=${DEV_ETH_RESERVE_AMOUNT:-""10000000000000000000000000000000000}
faucet_amount=${DEV_FAUCET_AMOUNT:-0}
DEV_ETH_KEYSTORE_FILE=${DEV_ETH_KEYSTORE_FILE:-`realpath ./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c`}

set -e

DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=`eth-checksum $(cat $DEV_ETH_KEYSTORE_FILE | jq -r .address)`

if [ ! -z $DEV_ETH_GAS_PRICE ]; then
	gas_price_arg="--gas-price $DEV_ETH_GAS_PRICE"
	>&2 echo using static gas price $DEV_ETH_GAS_PRICE
fi

if [[ $DEV_TOKEN_TYPE != 'giftable' && $DEV_TOKEN_TYPE != 'sarafu' ]]; then
	echo $DEV_TOKEN_TYPE
	>&2 echo DEV_TOKEN_TYPE must be one of [giftable,sarafu]
	exit 1
fi

echo "environment:"
printenv
echo \n

echo "using wallet address '$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER' from keystore file $DEV_ETH_KEYSTORE_FILE"

# This is a grassroots team convention for building the Bancor contracts using the bancor protocol repository truffle setup
# Running this in docker-internal dev container (built from Docker folder in this repo) will write a
# source-able env file to CIC_DATA_DIR. Services dependent on these contracts can mount this file OR 
# define these parameters at runtime
# pushd /usr/src

if [ -z $CIC_DATA_DIR ]; then
	CIC_DATA_DIR=`mktemp -d`
fi
>&2 echo using data dir $CIC_DATA_DIR

init_level_file=${CIC_DATA_DIR}/.init
if [ ! -f ${CIC_DATA_DIR}/.init ]; then
  echo "Creating .init file..."
  mkdir -p $CIC_DATA_DIR
  touch $CIC_DATA_DIR/.init
#   touch $init_level_file
fi
echo -n 1 > $init_level_file

# Abort on any error (including if wait-for-it fails).

# Wait for the backend to be up, if we know where it is.
if [[ -n "${ETH_PROVIDER}" ]]; then

	if [ ! -z "$DEV_USE_DOCKER_WAIT_SCRIPT" ]; then
		echo "waiting for ${ETH_PROVIDER}..."
		./wait-for-it.sh "${ETH_PROVIDER_HOST}:${ETH_PROVIDER_PORT}"
	fi

	if [ $DEV_TOKEN_TYPE == 'giftable' ]; then
		>&2 echo "deploying 'giftable token'"
		DEV_RESERVE_ADDRESS=`giftable-token-deploy $gas_price_arg -p $ETH_PROVIDER -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -vv -w --name "Giftable Token" --symbol "GFT" --decimals 6 -vv`
	else
		>&2 echo "deploying 'sarafu' token'"
		DEV_RESERVE_ADDRESS=`sarafu-token-deploy $gas_price_arg -p $ETH_PROVIDER -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -vv -w --name "Sarafu" --decimals 6 -vv SRF $DEV_SARAFU_DEMURRAGE_LEVEL`
	fi
	giftable-token-gift $gas_price_arg -p $ETH_PROVIDER -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -vv -w -a $DEV_RESERVE_ADDRESS $DEV_RESERVE_AMOUNT

	#BANCOR_REGISTRY_ADDRESS=`cic-bancor-deploy $gas_price_arg --bancor-dir /usr/local/share/cic/bancor -z $DEV_ETH_RESERVE_ADDRESS -p $ETH_PROVIDER -o $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`

	>&2 echo "deploy account index contract"
	DEV_ACCOUNT_INDEX_ADDRESS=`eth-accounts-index-deploy $gas_price_arg -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -y $DEV_ETH_KEYSTORE_FILE -vv -w`
	>&2 echo "add deployer address as account index writer"
	eth-accounts-index-writer $gas_price_arg -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_ACCOUNT_INDEX_ADDRESS -ww -vv $debug $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER

	CIC_REGISTRY_ADDRESS=`eth-contract-registry-deploy $gas_price_arg -i $CIC_CHAIN_SPEC -y $DEV_ETH_KEYSTORE_FILE --identifier BancorRegistry --identifier AccountRegistry --identifier TokenRegistry --identifier AddressDeclarator --identifier Faucet --identifier TransferAuthorization -p $ETH_PROVIDER -vv -w`
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $ETH_PROVIDER -vv ContractRegistry $CIC_REGISTRY_ADDRESS
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv AccountRegistry $DEV_ACCOUNT_INDEX_ADDRESS

	# Deploy address declarator registry
	>&2 echo "deploy address declarator contract"
	declarator_description=0x546869732069732074686520434943206e6574776f726b000000000000000000
	DEV_DECLARATOR_ADDRESS=`eth-address-declarator-deploy -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -vv $declarator_description`
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv AddressDeclarator $DEV_DECLARATOR_ADDRESS

	# Deploy transfer authorization contact
	>&2 echo "deploy address declarator contract"
	DEV_TRANSFER_AUTHORIZATION_ADDRESS=`erc20-transfer-auth-deploy $gas_price_arg -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -vv`
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $ETH_PROVIDER -vv TransferAuthorization $DEV_TRANSFER_AUTHORIZATION_ADDRESS

	# Deploy token index contract
	>&2 echo "deploy token index contract"
	DEV_TOKEN_INDEX_ADDRESS=`eth-token-index-deploy $gas_price_arg -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -vv`
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv TokenRegistry $DEV_TOKEN_INDEX_ADDRESS 
	>&2 echo "add reserve token to token index"
	eth-token-index-add $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE  -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv -a $DEV_TOKEN_INDEX_ADDRESS $DEV_RESERVE_ADDRESS

	# Sarafu faucet contract
	>&2 echo "deploy token faucet contract"
	DEV_FAUCET_ADDRESS=`sarafu-faucet-deploy $gas_price_arg -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -w -vv --account-index-address $DEV_ACCOUNT_INDEX_ADDRESS $DEV_RESERVE_ADDRESS`
	eth-contract-registry-set $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -r $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv Faucet $DEV_FAUCET_ADDRESS
	>&2 echo "set faucet as token minter"
	giftable-token-minter $gas_price_arg -w -y $DEV_ETH_KEYSTORE_FILE -a $DEV_RESERVE_ADDRESS -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -vv $DEV_FAUCET_ADDRESS

	>&2 echo "set token faucet amount"
	sarafu-faucet-set $gas_price_arg -y $DEV_ETH_KEYSTORE_FILE -i $CIC_CHAIN_SPEC -p $ETH_PROVIDER -a $DEV_FAUCET_ADDRESS -vv $faucet_amount

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
