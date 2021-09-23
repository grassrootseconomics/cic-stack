#! /bin/bash

>&2 echo -e "\033[;96mRUNNING\033[;39m configurations"
./config.sh
if [ $? -ne "0" ]; then
	>&2 echo -e "\033[;31mFAILED\033[;39m configurations"
	exit 1;
fi
>&2 echo -e "\033[;32mSUCCEEDED\033[;39m configurations"

if [[ $((RUN_MASK & 1)) -eq 1 ]]
then
	>&2 echo -e "\033[;96mRUNNING\033[;39m RUN_MASK 1 - contract deployment"
	./reset.sh
  ./docker/init_readyz.sh 2>&1 &
	if [ $? -ne "0" ]; then
		>&2 echo -e "\033[;31mFAILED\033[;39m RUN_MASK 1 - contract deployment"
		exit 1;
	fi
	>&2 echo -e "\033[;32mSUCCEEDED\033[;39m RUN_MASK 1 - contract deployment"
fi

if [[ $((RUN_MASK & 2)) -eq 2 ]]
then
	>&2 echo -e "\033[;96mRUNNING\033[;39m RUN_MASK 2 - custodial service initialization"
	./seed_cic_eth.sh
  ./docker/init_readyz.sh
	if [ $? -ne "0" ]; then
		>&2 echo -e "\033[;31mFAILED\033[;39m RUN_MASK 2 - custodial service initialization"
		exit 1;
	fi
	>&2 echo -e "\033[;32mSUCCEEDED\033[;39m RUN_MASK 2 - custodial service initialization"
fi


