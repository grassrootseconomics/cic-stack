export DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=${DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER:-"0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C"}
export DEV_ETH_GENESIS_START_GAS=${DEV_ETH_GENESIS_START_GAS:-"0x204fce5e3e25026110000000"}
export DEV_ETH_ACCOUNT_VALIDATOR="0x$(eth-keyfile -d keyfile_validator.json)"
export DEV_ETH_GENESIS_EXTRA_DATA="0x$(cat .extra)"

bash aux/bash-templater/templater.sh kitabu.json.template > kitabu.json

mkdir -vp .openethereum/data/keys/kitabu_sarafu
cp -v keyfile_validator.json .openethereum/data/keys/kitabu_sarafu/

export CONFIG_DIR=$(pwd)
export DATA_DIR="$CONFIG_DIR/.openethereum"
export SIGNER_ADDRESS=$DEV_ETH_ACCOUNT_VALIDATOR
export LOG_DIR=$CONFIG_DIR

bash aux/bash-templater/templater.sh kitabu.toml.template > kitabu.toml