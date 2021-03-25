#! /bin/bash

if [[ $((RUN_MASK & 1)) -eq 1 ]]
then
  ./reset.sh
fi

if [[ $((RUN_MASK & 2)) -eq 2 ]]
then
  ./seed_cic_eth.sh
fi
