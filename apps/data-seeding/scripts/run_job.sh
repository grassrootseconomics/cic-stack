#! /bin/bash

if [[ $((RUN_MASK & 3)) -eq 3 ]]
then
	>&2 echo -e "\033[;96mRUNNING\033[;39m RUN_MASK 3 - data seeding"

    contract_migration_complete=0
    retry_count=0
    retry_sleep=30 #seconds
    retry_limit="$((${TIMEOUT_MINUTES:-10}*60/2))"
    while [[ $contract_migration_complete -ne 1 ]]
    do
      if [[ -f "$CIC_DATA_DIR/.env"  ]] && grep -q CIC_DECLARATOR_ADDRESS $CIC_DATA_DIR/.env
      then
        echo "🤜💥🤛 data-seeding found the output of contract-migration!"
        source /tmp/cic/config/.env
        env
        contract_migration_complete=1
        ./scripts/run_ussd_user_imports.sh
      elif [[ $retry_count -ge $retry_limit ]] 
      then
        echo "😢 data-seeding timeout waiting for contract migration to finish." >&2
        exit 1
      else
        echo "⏳ data-seeding waiting for contract-migration output $retry_count:$retry_limit ..."
        ((retry_count= $retry_count + $retry_sleep))
        sleep $retry_sleep 
      fi
    done
  
	if [ $? -ne "0" ]; then
		>&2 echo -e "\033[;31mFAILED\033[;39m RUN_MASK 3 - data seeding"
		exit 1;
	fi
	>&2 echo -e "\033[;32mSUCCEEDED\033[;39m RUN_MASK 3 - data seeding"
fi
