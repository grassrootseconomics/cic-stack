#!/bin/bash

set -a

. ${DEV_DATA_DIR}/env_reset

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}

set -e

if [ ! -z $DEV_ETH_GAS_PRICE ]; then
	gas_price_arg="--gas-price $DEV_ETH_GAS_PRICE"
	fee_price_arg="--fee-price $DEV_ETH_GAS_PRICE"
fi

# Wait for the backend to be up, if we know where it is.
if [ -z "${RPC_PROVIDER}" ]; then
	echo "\$RPC_PROVIDER not set!"
	exit 1
fi

unset CONFINI_DIR

if [ ! -z "$DEV_USE_DOCKER_WAIT_SCRIPT" ]; then
	IFS=: read -a p <<< "$RPC_PROVIDER"
	read -i "/" rpc_provider_port <<< "${p[2]}"
	rpc_provider_host=${p[1]:2}
	echo "waiting for provider host $rpc_provider_host port $rpc_provider_port..."
	./wait-for-it.sh "$rpc_provider_host:$rpc_provider_port" -t $WAIT_FOR_TIMEOUT
fi

if [ "$TOKEN_TYPE" == "giftable_erc20_token" ]; then
	if [ -z "$TOKEN_SYMBOL" ]; then
		>&2 echo token symbol not set, setting defaults for type $TOKEN_TYPE
		TOKEN_SYMBOL="GFT"
		TOKEN_NAME="Giftable Token"
	elif [ -z "$TOKEN_NAME" ]; then
		>&2 echo token name not set, setting same as symbol for type $TOKEN_TYPE
		TOKEN_NAME=$TOKEN_SYMBOL
	fi
	>&2 echo deploying default token $TOKEN_TYPE
	echo giftable-token-deploy $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -vv -s -ww --name "$TOKEN_NAME" --symbol $TOKEN_SYMBOL --decimals 6 -vv
	DEV_RESERVE_ADDRESS=`giftable-token-deploy $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -vv -s -ww --name "$TOKEN_NAME" --symbol $TOKEN_SYMBOL --decimals 6 -vv`
elif [ "$TOKEN_TYPE" == "erc20_demurrage_token" ]; then
	if [ -z "$TOKEN_SYMBOL" ]; then
		>&2 echo token symbol not set, setting defaults for type $TOKEN_TYPE
		TOKEN_SYMBOL="DET"
		TOKEN_NAME="Demurrage Token"
	elif [ -z "$TOKEN_NAME" ]; then
		>&2 echo token name not set, setting same as symbol for type $TOKEN_TYPE
		TOKEN_NAME=$TOKEN_SYMBOL
	fi
	>&2 echo deploying token $TOKEN_TYPE
	if [ -z $TOKEN_SINK_ADDRESS ]; then
		if [ ! -z $TOKEN_REDISTRIBUTION_PERIOD ]; then
			>&2 echo -e "\033[;93mtoken sink address not set, so redistribution will be BURNED\033[;39m"
		fi
	fi
	DEV_RESERVE_ADDRESS=`erc20-demurrage-token-deploy $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC --name "$TOKEN_NAME" --symbol $TOKEN_SYMBOL -vv -ww -s` 
else
	>&2 echo unknown token type $TOKEN_TYPE
	exit 1
fi

echo "giftable-token-gift $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -vv -w -e $DEV_RESERVE_ADDRESS $DEV_RESERVE_AMOUNT"
giftable-token-gift $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -u -vv -s -w -e $DEV_RESERVE_ADDRESS $DEV_RESERVE_AMOUNT

# Deploy address declarator registry
>&2 echo "deploy address declarator contract"
declarator_description=0x546869732069732074686520434943206e6574776f726b000000000000000000
DEV_DECLARATOR_ADDRESS=`eth-address-declarator-deploy -s -u -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -w -vv $declarator_description`

>&2 echo "deploy contract registry contract"
#CIC_REGISTRY_ADDRESS=`eth-contract-registry-deploy $fee_price_arg -i $CIC_CHAIN_SPEC -y $WALLET_KEY_FILE --identifier AccountRegistry --identifier TokenRegistry --identifier AddressDeclarator --identifier Faucet --identifier TransferAuthorization --identifier ContractRegistry -p $RPC_PROVIDER -vv -s -u -w`
CIC_REGISTRY_ADDRESS=`okota-contract-registry-deploy $fee_price_arg -i $CIC_CHAIN_SPEC -y $WALLET_KEY_FILE --identifier AccountRegistry --identifier TokenRegistry --identifier AddressDeclarator --identifier Faucet --identifier TransferAuthorization --identifier ContractRegistry --address-declarator $DEV_DECLARATOR_ADDRESS -p $RPC_PROVIDER -vv -s -u -w`
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $RPC_PROVIDER -vv --identifier ContractRegistry $CIC_REGISTRY_ADDRESS

eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv --identifier AddressDeclarator $DEV_DECLARATOR_ADDRESS

>&2 echo "deploy account index contract"
#DEV_ACCOUNT_INDEX_ADDRESS=`eth-accounts-index-deploy $fee_price_arg -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -y $WALLET_KEY_FILE -vv -s -u -w`
DEV_ACCOUNT_INDEX_ADDRESS=`okota-accounts-index-deploy $fee_price_arg -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -y $WALLET_KEY_FILE -vv -s -u -w --address-declarator $DEV_DECLARATOR_ADDRESS --token-address $DEV_RESERVE_ADDRESS`
#>&2 echo "add deployer address as account index writer"
#eth-accounts-index-writer $fee_price_arg -s -u -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -e $DEV_ACCOUNT_INDEX_ADDRESS -ww -vv $debug $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv --identifier AccountRegistry $DEV_ACCOUNT_INDEX_ADDRESS

# Deploy transfer authorization contact
>&2 echo "deploy transfer auth contract"
DEV_TRANSFER_AUTHORIZATION_ADDRESS=`erc20-transfer-auth-deploy $gas_price_arg -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -w -vv`
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC  -p $RPC_PROVIDER -vv --identifier TransferAuthorization $DEV_TRANSFER_AUTHORIZATION_ADDRESS

# Deploy token index contract
>&2 echo "deploy token index contract"
#DEV_TOKEN_INDEX_ADDRESS=`eth-token-index-deploy -s -u $fee_price_arg -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -w -vv`
DEV_TOKEN_INDEX_ADDRESS=`okota-token-index-deploy -s -u $fee_price_arg -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -w -vv --address-declarator $DEV_DECLARATOR_ADDRESS`
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv --identifier TokenRegistry $DEV_TOKEN_INDEX_ADDRESS 
>&2 echo "add reserve token to token index"
eth-token-index-add $fee_price_arg -s -u -w -y $WALLET_KEY_FILE  -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv -e $DEV_TOKEN_INDEX_ADDRESS $DEV_RESERVE_ADDRESS

# Sarafu faucet contract
>&2 echo "deploy token faucet contract"
DEV_FAUCET_ADDRESS=`sarafu-faucet-deploy $fee_price_arg -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -w -vv --account-index-address $DEV_ACCOUNT_INDEX_ADDRESS $DEV_RESERVE_ADDRESS -s`

>&2 echo "set token faucet amount"
sarafu-faucet-set $fee_price_arg -w -y $WALLET_KEY_FILE -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -e $DEV_FAUCET_ADDRESS -vv -s --fee-limit 100000 $DEV_FAUCET_AMOUNT

>&2 echo "register faucet in registry"
eth-contract-registry-set -s -u $fee_price_arg -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv --identifier Faucet $DEV_FAUCET_ADDRESS

>&2 echo "set faucet as token minter"
giftable-token-minter -s -u $fee_price_arg -w -y $WALLET_KEY_FILE -e $DEV_RESERVE_ADDRESS -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -vv $DEV_FAUCET_ADDRESS


#echo "export CIC_DEFAULT_TOKEN_SYMBOL=$TOKEN_SYMBOL" >> ${DEV_DATA_DIR}/env_reset
export CIC_DEFAULT_TOKEN_SYMBOL=$TOKEN_SYMBOL

echo "Writing env_reset file ..."

echo "export CIC_REGISTRY_ADDRESS=$CIC_REGISTRY_ADDRESS
export CIC_DEFAULT_TOKEN_SYMBOL=$CIC_DEFAULT_TOKEN_SYMBOL
export TOKEN_NAME=$TOKEN_NAME
" >> "${DEV_DATA_DIR}"/env_reset

confini-dump --schema-dir ./config
eth-contract-registry-list -i $CIC_CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS -u

set +a
set +e

exec "$@"
