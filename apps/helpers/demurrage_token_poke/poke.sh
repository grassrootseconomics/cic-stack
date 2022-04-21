#!/bin/bash

default_token_address=`eth-contract-registry-list --raw -e $CIC_REGISTRY_ADDRESS DefaultToken`
export TOKEN_ADDRESSES=${TOKEN_ADDRESSES:-$default_token_address}

IFS="," read -r -a token_addresses <<< $TOKEN_ADDRESSES
export RPC_VERIFY=1

for token_address in ${token_addresses[@]}; do
	>&2 echo checking token address $token_address
	t=`eth-encode --signature demurrageTimestamp -e $token_address --notx`
	v=`eth-encode --signature demurrageAmount -e $token_address --notx`
	>&2 echo last demurrage apply call for $token_address was value $v at $t 
	if [ "$?" -eq 0 ]; then
		h=`eth-encode --signature applyDemurrage -i $CHAIN_SPEC -y $WALLET_KEY_FILE -e $token_address --fee-limit 8000000 -s -ww`
		>&2 echo applied demurrage on $token_address tx hash $h
	fi
done
