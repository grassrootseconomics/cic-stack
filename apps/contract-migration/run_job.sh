#! /bin/bash

if [[ $RUN_LEVEL -gt 0 ]]
then
  ./reset.sh
fi

if [[ $RUN_LEVEL -gt 1 ]]
then
  ./seed_cic_eth.sh
fi