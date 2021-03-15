# DATA GENERATION TOOLS

This folder contains tools to generate and import test data.

## DATA CREATION

Does not need the cluster to run.

Vanilla:

`python create_import_users.py [--dir <datadir>] <number_of_users>`

If you want to use the `import_balance.py` script to add to the user's balance from an external address, add:

`python create_import_users.py --gift-threshold <max_units_to_send> [--dir <datadir>] <number_of_users>`


## IMPORT

Make sure the following is running in the cluster:
	* eth
	* postgres
	* redis
	* cic-eth-tasker
	* cic-eth-dispatcher
	* cic-eth-manager-head


You will want to run these in sequence:


## 1. Metadata

`node import_meta.js <datadir> <number_of_users>`

Monitors a folder for output from the `import_users.py` script, adding the metadata found to the `cic-meta` service.


## 2. Balances

(Only if you used the `--gift-threshold` option above)

`python -c config -i <newchain:id> -r <cic_registry_address> -p <eth_provider> --head -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c <datadir>` 

This will monitor new mined blocks and send balances to the newly created accounts.


### 3. Users

Without any modifications to the cluster and config files:

`python import_users.py -c config --redis-host-callback redis <datadir>`

** A note on the The callback**:  The script uses a redis callback to retrieve the newly generated custodial address. This is the redis server _from the perspective of the cic-eth component_.


## VERIFY

`python verify.py -c config -i <newchain:id> -r <cic_registry_address> -p <eth_provider> <datadir>` 

Checks
	* Private key is in cic-eth keystore
	* Address is in accounts index
	* Address has balance matching the gift threshold 
	* Metadata can be retrieved and has exact match

Should exit with code 0 if all input data is found in the respective services.


## KNOWN ISSUES

If the faucet disbursement is set to a non-zero amount, the balances will be off. The verify script needs to be improved to check the faucet amount.