#!/bin/bash

set -a

if [ -z $DEV_DATA_DIR ]; then
	export DEV_DATA_DIR=`mktemp -d`
else
	mkdir -p $DEV_DATA_DIR
fi

if [ -z $DEV_CONFIG_RESET ]; then
	if [ -f ${DEV_DATA_DIR}/env_reset ]; then
		>&2 echo "importing existing configuration values from ${DEV_DATA_DIR}/env_reset"
		. ${DEV_DATA_DIR}/env_reset
	fi
fi

# Handle wallet
export WALLET_KEY_FILE=${WALLET_KEY_FILE:-`realpath ./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c`}
if [ ! -f $WALLET_KEY_FILE ]; then
	>&2 echo "wallet path '$WALLET_KEY_FILE' does not point to a file"
	exit 1
fi
export DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=`eth-checksum $(cat $WALLET_KEY_FILE | jq -r .address)`

# Wallet dependent variable defaults
export DEV_ETH_ACCOUNT_RESERVE_MINTER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export CIC_TRUST_ADDRESS=${CIC_TRUST_ADDRESS:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export CIC_DEFAULT_TOKEN_SYMBOL=$TOKEN_SYMBOL
export TOKEN_SINK_ADDRESS=${TOKEN_SINK_ADDRESS:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}


# Legacy variable defaults


# Migration variable processing

confini-dump --schema-module chainlib.eth.data.config --schema-module cic_eth.data.config --schema-dir ./config --prefix export > ${DEV_DATA_DIR}/env_reset

cat ${DEV_DATA_DIR}/env_reset

set +a
