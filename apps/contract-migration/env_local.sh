#!/bin/bash

set +a
if [ ! -z "$DEV_CONFIG_RESET" ]; then
	export DEV_SESSION=$(uuidgen)
	export CHAIN_SPEC=${CHAIN_SPEC:-evm:kitabu:5050:sarafu}
fi
if [ -z "$DEV_SESSION" ]; then
	export DEV_SESSION=${DEV_SESSION:-$(uuidgen)}
	export CHAIN_SPEC=${CHAIN_SPEC:-evm:kitabu:5050:sarafu}
fi
uid=`id -z -u`
export DEV_DATA_DIR="/run/user/$uid/cic-stack/$DEV_SESSION"
mkdir -vp $DEV_DATA_DIR

export REDIS_HOST=localhost
export REDIS_PORT=6379
export CELERY_BROKER_URL="redis://$REDIS_HOST:$REDIS_PORT"
export CELERY_RESULT_URL=$CELERY_BROKER_URL
export DEV_FEE_PRICE=1
export RPC_PROVIDER=http://localhost:8545

#export WALLET_KEY_FILE=${WALLET_KEY_FILE:-./keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c}
#export WALLET_PASSPHRASE=${WALLET_PASSPHRASE:-''}
#export PGP_PASSPHRASE=merman
#export PGP_PRIVATEKEY_FILE=pgp/merman.priv.asc
#export PGP_FINGERPRINT=F3FAF668E82EF5124D5187BAEF26F4682343F692
#export TOKEN_SUPPLY_LIMIT=
#export TOKEN_DEMURRAGE_LEVEL=46124891913883000000000000000000
#export TOKEN_SINK_ADDRESS=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
#export TOKEN_REDISTRIBUTION_PERIOD=10800
#export TOKEN_TYPE=giftable_erc20_token
#export TOKEN_SYMBOL=GFT
#export TOKEN_NAME=Giftable Token
#export DEV_TOKEN_MINT_AMOUNT=2000000000000
#export DEV_GAS_AMOUNT=10000000000000000000000
#export DEV_TOKEN_DATA_PATH=./token_data/default

set -a

>&2 echo "using session $DEV_SESSION"
