#! /bin/bash

if [[ $((RUN_MASK & 1)) -eq 1 ]]
then
	./reset.sh
	if [ $? -ne "0" ]; then
	  exit 1;
	fi
fi

if [[ $((RUN_MASK & 2)) -eq 2 ]]
then
	./seed_cic_eth.sh
fi
