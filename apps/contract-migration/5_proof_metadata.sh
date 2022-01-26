#!/bin/bash

. util.sh

set -a

. ${DEV_DATA_DIR}/env_reset

set -e

>&2 echo -e "\033[;96mWriting token metadata and proofs\033[;39m"
python scripts/proofs.py --write-metadata --token-symbol $TOKEN_SYMBOL -e $TOKEN_ADDRESS --address-declarator $DEV_ADDRESS_DECLARATOR --signer-address $DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER

>&2 echo -e "\033[;96mWriting env_reset file\033[;39m"
confini-dump --schema-dir ./config > ${DEV_DATA_DIR}/env_reset

set +e
set +a
