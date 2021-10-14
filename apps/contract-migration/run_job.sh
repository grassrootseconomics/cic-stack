#! /bin/bash

. ./util.sh

set -a
DEV_DEBUG_FLAG=""
DEV_DEBUG_LEVEL=${DEV_DEBUG_LEVEL=0}
if [ $DEV_DEBUG_LEVEL -eq 1 ]; then
	DEV_DEBUG_FLAG="-v"
elif [ $DEV_DEBUG_LEVEL -gt 1 ]; then
	DEV_DEBUG_FLAG="-vv"
fi

# disable override of config schema directory
unset CONFINI_DIR

set +a

LAST_BIT_POS=4
files=(deploy_contract_root deploy_contract_instance deploy_token)
description=("global contracts" "instance specific contracts" "token deployment")

>&2 echo -e "\033[;96mRUNNING configurations\033[;39m"
source ./config.sh
if [ $? -ne "0" ]; then
	>&2 echo -e "\033[;31mFAILED configurations\033[;39m"
	exit 1;
fi
>&2 echo -e "\033[;32mSUCCEEDED configurations\033[;39m"

>&2 echo -e "\033[;96mInitial configuration state\033[;39m"

confini-dump --schema-dir ./config

clear_pending_tx_hashes


bit=1
for ((i=0; i<$LAST_BIT_POS; i++)); do
	runlevel="RUNLEVEL $bit"
	if [[ $((RUN_MASK & $bit)) -eq ${bit} ]]; then
		s="$runlevel - ${description[$i]}"
		>&2 echo -e "\033[;96mRUNNING $s\033[;39m"
		source $((i+1))_${files[$i]}.sh
		if [ $? -ne "0" ]; then
			>&2 echo -e "\033[;31mFAILED $s\033[;39m"
			exit 1;
		fi
		>&2 echo -e "\033[;32mSUCCEEDED $s\033[;39m"
		echo -e "\033[;96mConfiguration state after $runlevel execution\033[;39m"
		confini-dump --schema-dir ./config
	fi
	bit=$((bit*2))
done
