#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}

set -e

must_address "$DEV_ADDRESS_DECLARATOR" "address declarator"
must_eth_rpc

if [ ! -z $DEV_ETH_GAS_PRICE ]; then
	gas_price_arg="--gas-price $DEV_ETH_GAS_PRICE"
	fee_price_arg="--fee-price $DEV_ETH_GAS_PRICE"
fi



# Deploy contract registry contract
>&2 echo -e "\033[;96mDeploy contract registry contract\033[;39m"
CIC_REGISTRY_ADDRESS=`okota-contract-registry-deploy $fee_price_arg -i $CHAIN_SPEC -y $WALLET_KEY_FILE --identifier AccountRegistry --identifier TokenRegistry --identifier AddressDeclarator --identifier Faucet --identifier TransferAuthorization --identifier ContractRegistry --identifier DefaultToken --address-declarator $DEV_ADDRESS_DECLARATOR -p $RPC_PROVIDER $DEV_DEBUG_FLAG -s -u -w`

>&2 echo -e "\033[;96mAdd contract registry record to itself\033[;39m"
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC  -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier ContractRegistry $CIC_REGISTRY_ADDRESS

>&2 echo -e "\033[;96mAdd address declarator record to contract registry\033[;39m"
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier AddressDeclarator $DEV_ADDRESS_DECLARATOR


# Deploy accounts index contact
#>&2 echo -e "\033[;96mdeploy accounts index contract\033[;39m"
#DEV_ACCOUNT_INDEX_ADDRESS=`okota-accounts-index-deploy $fee_price_arg -i $CHAIN_SPEC -p $RPC_PROVIDER -y $WALLET_KEY_FILE $DEV_DEBUG_FLAG -s -u -w --address-declarator $DEV_ADDRESS_DECLARATOR --token-address $DEV_RESERVE_ADDRESS`
#>&2 echo "add deployer address as account index writer"
#eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier AccountRegistry $DEV_ACCOUNT_INDEX_ADDRESS


# Deploy transfer authorization contact
>&2 echo -e "\033[;96mDeploy transfer authorization contract\033[;39m"
DEV_TRANSFER_AUTHORIZATION_ADDRESS=`erc20-transfer-auth-deploy $gas_price_arg -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG`

>&2 echo -e "\033[;96mAdd transfer authorization record to contract registry\033[;39m"
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC  -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier TransferAuthorization $DEV_TRANSFER_AUTHORIZATION_ADDRESS


# Deploy token index contract
>&2 echo -e "\033[;96mDeploy token symbol index contract\033[;39m"
DEV_TOKEN_INDEX_ADDRESS=`okota-token-index-deploy -s -u $fee_price_arg -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG --address-declarator $DEV_ADDRESS_DECLARATOR`

>&2 echo -e "\033[;96mAdd token symbol index record to contract registry\033[;39m"
eth-contract-registry-set $fee_price_arg -s -u -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier TokenRegistry $DEV_TOKEN_INDEX_ADDRESS 

#>&2 echo "add reserve token to token index"
#eth-token-index-add $fee_price_arg -s -u -w -y $WALLET_KEY_FILE  -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG -e $DEV_TOKEN_INDEX_ADDRESS $DEV_RESERVE_ADDRESS


## Sarafu faucet contract
#>&2 echo "deploy token faucet contract"
#DEV_FAUCET_ADDRESS=`sarafu-faucet-deploy $fee_price_arg -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -w $DEV_DEBUG_FLAG --account-index-address $DEV_ACCOUNT_INDEX_ADDRESS $DEV_RESERVE_ADDRESS -s`
#
#>&2 echo "set token faucet amount"
#sarafu-faucet-set $fee_price_arg -w -y $WALLET_KEY_FILE -i $CHAIN_SPEC -p $RPC_PROVIDER -e $DEV_FAUCET_ADDRESS $DEV_DEBUG_FLAG -s --fee-limit 100000 $DEV_FAUCET_AMOUNT
#
#>&2 echo "register faucet in registry"
#eth-contract-registry-set -s -u $fee_price_arg -w -y $WALLET_KEY_FILE -e $CIC_REGISTRY_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG --identifier Faucet $DEV_FAUCET_ADDRESS

#>&2 echo "set faucet as token minter"
#giftable-token-minter -s -u $fee_price_arg -w -y $WALLET_KEY_FILE -e $DEV_RESERVE_ADDRESS -i $CHAIN_SPEC -p $RPC_PROVIDER $DEV_DEBUG_FLAG $DEV_FAUCET_ADDRESS

echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config --prefix export > ${DEV_DATA_DIR}/env_reset

#echo "export CIC_REGISTRY_ADDRESS=$CIC_REGISTRY_ADDRESS
#export CIC_DEFAULT_TOKEN_SYMBOL=$CIC_DEFAULT_TOKEN_SYMBOL
#export TOKEN_NAME=$TOKEN_NAME
#" >> "${DEV_DATA_DIR}"/env_reset

set +a
set +e
