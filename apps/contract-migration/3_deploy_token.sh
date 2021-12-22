#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}

set -e

if [ ! -z $DEV_FEE_PRICE ]; then
	gas_price_arg="--gas-price $DEV_FEE_PRICE"
	fee_price_arg="--fee-price $DEV_FEE_PRICE"
fi

have_default_token=1
token_feedback_display_string='token'

must_address "$DEV_ADDRESS_DECLARATOR" "address declarator"
must_address "$CIC_REGISTRY_ADDRESS" "registry"
must_eth_rpc


function _deploy_token_defaults {
	if [ -z "$TOKEN_SYMBOL" ]; then
		>&2 echo -e "\033[;33mToken symbol not set, setting defaults for type $TOKEN_TYPE\033[;39m"
		TOKEN_SYMBOL=$1
		TOKEN_NAME=$2
	elif [ -z "$TOKEN_NAME" ]; then
		>&2 echo -e "\033[;33mToken name not set, setting same as symbol for type $TOKEN_TYPE\033[;39m"
		TOKEN_NAME=$TOKEN_SYMBOL
	fi
	TOKEN_DECIMALS=${TOKEN_DECIMALS:-6}

	debug_rpc
	default_token_registered=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw DefaultToken --fee-limit 8000000`
	if [ $default_token_registered == '0000000000000000000000000000000000000000' ]; then
		>&2 echo -e "\033[;33mFound no existing default token in token registry"
		have_default_token=''
		token_feedback_display_string='default token'
	fi
	>&2 echo -e "\033[;96mdeploying $token_feedback_display_string ..."
	>&2 echo -e "Type: $TOKEN_TYPE"
	>&2 echo -e "Name: $TOKEN_NAME"
	>&2 echo -e "Symbol: $TOKEN_SYMBOL"
	>&2 echo -e "Decimals: $TOKEN_DECIMALS\033[;39m"

}

function deploy_token_giftable_erc20_token() {
	_deploy_token_defaults "GFT" "Giftable Token"
	advance_nonce
	debug_rpc
	TOKEN_ADDRESS=`giftable-token-deploy --nonce $nonce $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CHAIN_SPEC -s -ww --name "$TOKEN_NAME" --symbol $TOKEN_SYMBOL --decimals $TOKEN_DECIMALS $DEV_DEBUG_FLAG`
}


function deploy_token_erc20_demurrage_token() {
	_deploy_token_defaults "DET" "Demurrage Token"
	advance_nonce
	debug_rpc
	TOKEN_ADDRESS=`erc20-demurrage-token-deploy --nonce $nonce $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CHAIN_SPEC --name "$TOKEN_NAME" --symbol $TOKEN_SYMBOL $DEV_DEBUG_FLAG -ww -s` 
}

function deploy_accounts_index() {
	# Deploy accounts index contact
	>&2 echo -e "\033[;96mDeploy accounts index contract for token $TOKEN_SYMBOL\033[;39m"
	advance_nonce
	debug_rpc
	DEV_ACCOUNTS_INDEX_ADDRESS=`okota-accounts-index-deploy --nonce $nonce $fee_price_arg -u -s -w -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --address-declarator $DEV_ADDRESS_DECLARATOR --token-address $1`

	if [ -z "$have_default_token" ]; then
		advance_nonce
		debug_rpc
		>&2 echo -e "\033[;96mAdd acccounts index record for default token to contract registry\033[;39m"
		r=`eth-contract-registry-set --nonce $nonce $DEV_WAIT_FLAG $fee_price_arg -s -u -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC  -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier AccountRegistry $DEV_ACCOUNTS_INDEX_ADDRESS`
		add_pending_tx_hash $r
	fi
}

function deploy_minter_faucet() {
	FAUCET_AMOUNT=${FAUCET_AMOUNT:-0}

	# Token faucet contract
	advance_nonce
	debug_rpc
	>&2 echo -e "\033[;96mDeploy token faucet contract for token $TOKEN_SYMBOL\033[;39m"
	accounts_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw AccountRegistry  --fee-limit 8000000`
	faucet_address=`sarafu-faucet-deploy --nonce $nonce $fee_price_arg -s -w -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --account-index-address $accounts_index_address $1`

	# sarafu-faucet-deploy consumes TWO nonces
	advance_nonce
	advance_nonce
	debug_rpc
	>&2 echo -e "\033[;96mSet token faucet amount to $FAUCET_AMOUNT\033[;39m"
	r=`sarafu-faucet-set --nonce $nonce $fee_price_arg $DEV_WAIT_FLAG -s -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -e $faucet_address $DEV_DEBUG_FLAG --fee-limit 100000 $FAUCET_AMOUNT`
	add_pending_tx_hash $r

	if [ -z $have_default_token ]; then
		advance_nonce
		debug_rpc
		>&2 echo -e "\033[;96mRegister faucet in registry\033[;39m"
		r=`eth-contract-registry-set --nonce $nonce $DEV_WAIT_FLAG -s -u $fee_price_arg -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier Faucet $faucet_address`
		add_pending_tx_hash $r
	fi

	advance_nonce
	debug_rpc
	>&2 echo -e "\033[;96mSet faucet as token minter\033[;39m"
	r=`giftable-token-minter $DEV_WAIT_FLAG --nonce $nonce -s -u $fee_price_arg -y $WALLET_KEY_FILE -e $TOKEN_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG $faucet_address`
	add_pending_tx_hash $r
}


TOKEN_TYPE=${TOKEN_TYPE:-giftable_erc20_token}
deploy_token_${TOKEN_TYPE}

if [ -z "$have_default_token" ]; then
	advance_nonce
	debug_rpc
	>&2 echo -e "\033[;96mAdd default token to contract registry\033[;39m"
	r=`eth-contract-registry-set $DEV_WAIT_FLAG --nonce $nonce $fee_price_arg -s -u -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier DefaultToken $TOKEN_ADDRESS`
	add_pending_tx_hash $r
fi

advance_nonce
debug_rpc
>&2 echo -e "\033[;96mAdd token symbol $TOKEN_SYMBOL to token address $TOKEN_ADDRESS mapping to token index\033[;39m"
token_index_address=`eth-contract-registry-list -u -i $CHAIN_SPEC -p $RPC_PROVIDER -e $CIC_REGISTRY_ADDRESS $DEV_DEBUG_FLAG --raw TokenRegistry`
r=`eth-token-index-add --nonce $nonce $fee_price_arg -s -u -y $WALLET_KEY_FILE  -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG -e $token_index_address $TOKEN_ADDRESS`
add_pending_tx_hash $r


TOKEN_MINT_AMOUNT=${TOKEN_MINT_AMOUNT:-${DEV_TOKEN_MINT_AMOUNT}}
advance_nonce
debug_rpc
>&2 echo -e "\033[;96mMinting $TOKEN_MINT_AMOUNT tokens\033[;39m"
r=`giftable-token-gift $DEV_WAIT_FLAG --nonce $nonce $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CHAIN_SPEC -u $DEV_DEBUG_FLAG -s -e $TOKEN_ADDRESS "$DEV_TOKEN_MINT_AMOUNT"`
add_pending_tx_hash $r


# Create accounts index for default token
deploy_accounts_index $TOKEN_ADDRESS

# Connect a minter component if defined
TOKEN_MINTER_MODE=${TOKEN_MINTER_MODE:-"faucet"}
if [ -z "$TOKEN_MINTER_MODE" ]; then
	>&2 echo -e "\033[;33mNo token minter mode set.\033[;39m"
else
	deploy_minter_${TOKEN_MINTER_MODE} $TOKEN_ADDRESS
fi

>&2 echo -e "\033[;96mTransfer a single token to self to poke the gas cacher\033[;39m"
advance_nonce
debug_rpc
r=`erc20-transfer $DEV_WAIT_FLAG --nonce $nonce $fee_price_arg -p $RPC_PROVIDER -y $WALLET_KEY_FILE -i $CHAIN_SPEC -u $DEV_DEBUG_FLAG -s -e $TOKEN_ADDRESS -a $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER 1`
add_pending_tx_hash $r

check_wait 3

>&2 echo -e "\033[;96mWriting token metadata and proofs\033[;39m"
python scripts/proofs.py --token-symbol $TOKEN_SYMBOL -e $TOKEN_ADDRESS --address-declarator $DEV_ADDRESS_DECLARATOR --signer-address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER

>&2 echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +e
set +a
