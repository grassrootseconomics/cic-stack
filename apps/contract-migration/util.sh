function must_address() {
	if [[ ! "$1" =~ ^(0x)?[0-9a-fA-F]{40}$ ]]; then
		>&2 echo -e "\033[;31mvalue '$1' for $2 is not an address\033[;39m"
		exit 1	
	fi
}


function must_hash_256() {
	if [[ ! "$1" =~ ^(0x)?[0-9a-fA-F]{64}$ ]]; then
		>&2 echo -e "\033[;31mvalue '$1' for $2 is not a 256-bit digest\033[;39m"
		exit 1	
	fi
}


function must_eth_rpc() {
	if [ -z "${RPC_PROVIDER}" ]; then
		echo "\$RPC_PROVIDER not set!"
		exit 1
	fi
	# Wait for the backend to be up, if we know where it is.
	if [ ! -z "$DEV_USE_DOCKER_WAIT_SCRIPT" ]; then
		WAIT_FOR_TIMEOUT=${WAIT_FOR_TIMEOUT:-60}
		IFS=: read -a p <<< "$RPC_PROVIDER"
		read -i "/" rpc_provider_port <<< "${p[2]}"
		rpc_provider_host=${p[1]:2}
		echo "waiting for provider host $rpc_provider_host port $rpc_provider_port..."
		./wait-for-it.sh "$rpc_provider_host:$rpc_provider_port" -t $WAIT_FOR_TIMEOUT
	fi
}


function clear_pending_tx_hashes() {
	>&2 echo -e "\033[;96mClearing pending hashes\033[;39m"
	truncate -s 0 ${DEV_DATA_DIR}/hashes
}


function add_pending_tx_hash() {
	must_hash_256 $1
	echo $1 >> ${DEV_DATA_DIR}/hashes
}

function advance_nonce() {
	nonce=`cat $noncefile`
	next_nonce=$((nonce+1))
	echo -n $next_nonce > $noncefile
	if [ "$DEV_DEBUG_LEVEL" -gt 1 ]; then
		>&2 echo retrieved nonce $nonce
	fi
}

function debug_rpc() {
	if [ "$DEV_DEBUG_LEVEL" -gt 2 ]; then
		>&2 echo -e "\033[;35mRPC Node state\033[;39m"
		>&2 eth-info --local -p $RPC_PROVIDER
	fi
}

function check_wait() {
	#if [ "$1" -eq "$RUN_MASK_HIGHEST" ]; then
		>&2 echo -e "\033[;96mCatch up with paralell transactions\033[;39m"
		if [ "$DEV_DEBUG_LEVEL" -gt "0" ]; then
			>&2 cat ${DEV_DATA_DIR}/hashes
		fi
		eth-wait $DEV_DEBUG_FLAG -p $RPC_PROVIDER ${DEV_DATA_DIR}/hashes
		clear_pending_tx_hashes
	#fi
}
