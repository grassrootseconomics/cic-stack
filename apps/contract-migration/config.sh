#!/bin/bash

set -a
set -e

if [ -z $DEV_DATA_DIR ]; then
	export DEV_DATA_DIR=`mktemp -d`
else
	mkdir -p $DEV_DATA_DIR
fi

# Handle wallet
export WALLET_KEY_FILE=${WALLET_KEY_FILE:-`realpath ./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c`}
if [ ! -f $WALLET_KEY_FILE ]; then
	>&2 echo "wallet path '$WALLET_KEY_FILE' does not point to a file"
	exit 1
fi

export DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=`eth-keyfile -z -d $WALLET_KEY_FILE`
noncefile=${DEV_DATA_DIR}/nonce_${DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}

# By default configuration values generated from previous runs will be used in subsequent invocations
# Setting the config reset 
if [ -z $DEV_CONFIG_RESET ]; then
	if [ -f $DEV_DATA_DIR/env_reset ]; then
		>&2 echo -e "\033[;96mimporting existing configuration values from ${DEV_DATA_DIR}/env_reset\033[;39m"
		. ${DEV_DATA_DIR}/env_reset
	fi
else
	>&2 echo -e "\033[;33mGenerating scratch configuration\033[;39m"
	bash_debug_flag=""
	if [ "$DEV_DEBUG_LEVEL" -gt 1 ]; then
		bash_debug_flag="-v"
	fi
	rm $bash_debug_flag -f ${DEV_DATA_DIR}/env_reset
	rm $bash_debug_flag -f $noncefile
	export SYNCER_OFFSET=`eth-info --raw block`
	confini-dump --schema-dir ./config --prefix export > ${DEV_DATA_DIR}/env_reset
fi

# Wallet dependent variable defaults
export DEV_ETH_ACCOUNT_RESERVE_MINTER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export DEV_ETH_ACCOUNT_ACCOUNTS_INDEX_WRITER=${DEV_ETH_ACCOUNT_RESERVE_MINTER:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export CIC_TRUST_ADDRESS=${CIC_TRUST_ADDRESS:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}
export CIC_DEFAULT_TOKEN_SYMBOL=$TOKEN_SYMBOL
export TOKEN_SINK_ADDRESS=${TOKEN_SINK_ADDRESS:-$DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER}

if [ ! -f $noncefile ]; then
	nonce=`eth-count -p $RPC_PROVIDER $DEV_DEBUG_FLAG $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`
	>&2 echo -e "\033[;96mUsing contract deployer address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER with nonce $nonce\033[;39m"
	echo -n $nonce > $noncefile
else
	nonce=`cat $noncefile`
	>&2 echo -e "\033[;96mResuming usage with contract deployer address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER with nonce $nonce\033[;39m"
fi

if [ ! -f $noncefile ]; then
	nonce=`eth-count -p $RPC_PROVIDER $DEV_DEBUG_FLAG $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER`
	>&2 echo -e "\033[;96mUsing contract deployer address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER with nonce $nonce\033[;39m"
	echo -n $nonce > $noncefile
else
	nonce=`cat $noncefile`
	>&2 echo -e "\033[;96mResuming usage with contract deployer address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER with nonce $nonce\033[;39m"
fi

# Migration variable processing
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +e
set +a
