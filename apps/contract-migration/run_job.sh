#! /bin/bash

if [[ $RUN_LEVEL -eq 1 ]]
then
  ./reset.sh
fi

if [[ $RUN_LEVEL -eq 2 ]]
then
  ./seed_cic_eth.sh
fi
