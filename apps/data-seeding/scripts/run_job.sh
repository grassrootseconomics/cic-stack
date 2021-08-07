#! /bin/bash

if [[ $((RUN_MASK & 3)) -eq 3 ]]
then
	>&2 echo -e "\033[;96mRUNNING\033[;39m RUN_MASK 3 - data seeding"
	./scripts/run_ussd_user_imports.sh
	if [ $? -ne "0" ]; then
		>&2 echo -e "\033[;31mFAILED\033[;39m RUN_MASK 3 - data seeding"
		exit 1;
	fi
	>&2 echo -e "\033[;32mSUCCEEDED\033[;39m RUN_MASK 3 - data seeding"
fi
