# DATA GENERATION TOOLS

This folder contains tools to generate and import test data.

## OVERVIEW

Three sets of tools are available, sorted by respective subdirectories.

* **eth**: Import using sovereign wallets.
* **cic_eth**: Import using the `cic_eth` custodial engine.
* **cic_ussd**: Import using the `cic_ussd` interface (backed by `cic_eth`)

Each of the modules include two main scripts:

* **import_users.py**: Registers all created accounts in the network
* **import_balance.py**: Transfer an opening balance using an external keystore wallet

The balance script will sync with the blockchain, processing transactions and triggering actions when it finds. In its current version it does not keep track of any other state, so it will run indefinitly and needs You the Human to decide when it has done what it needs to do.


In addition the following common tools are available:

* User creation script
* Import verification script
* **cic_meta**: Metadata imports


## HOW TO USE

### Step 1 - Data creation

Before running any of the imports, the user data to import has to be generated and saved to disk.

The script does not need any services to run.

Vanilla version:

`python create_import_users.py [--dir <datadir>] <number_of_users>`

If you want to use a `import_balance.py` script to add to the user's balance from an external address, use:

`python create_import_users.py --gift-threshold <max_units_to_send> [--dir <datadir>] <number_of_users>`


### Step 2 - Services

Make sure the following is running in the cluster:
* eth
* postgres
* redis

If importing using `cic_eth` or `cic_ussd` also run:
* cic-eth-tasker
* cic-eth-dispatcher
* cic-eth-tracker

If importing using `cic_ussd` also run:
* cic-ussd-tasker
* cic-ussd-server
* cic-notify-tasker

If metadata is to be imported, also run:
* cic-meta-server


### Step 3 - User imports

Only run _one_ of the following.

#### Alternative 1 - Sovereign wallet import - `eth` 


First, make a note of the **block height** before running anything.

To import, run to _completion_:

`python eth/import_users.py -v -c config -p <eth_provider> -r <cic_registry_address> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c <datadir>`

If you are transferring balances externally, then run:

`python eth/import_balance.py -v -c config -r <cic_registry_address> -p <eth_provider> --offset <block_height_at_start> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c <datadir>` 




#### Alternative 2 - Custodial engine import - `cic_eth`

Run in sequence, in first terminal:

`python cic_eth/import_balance.py -v -c config -p http://localhost:63545 -r 0xea6225212005e86a4490018ded4bf37f3e772161 -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c --head out`

In another terminal:

`python cic_eth/import_users.py -v -c config --redis-host-callback <redis_hostname_in_docker> out`

The `redis_hostname_in_docker` value is the hostname required to reach the redis server from within the docker cluster. The `import_users` script will receive the address of each newly created custodial account on a redis subscription fed by a callback task in the `cic_eth` account creation task chain.


#### Alternative 3 - USSD import - `cic_ussd`

Run in sequence, in first terminal:

`python cic_eth/import_balance.py -v -c config -p http://localhost:63545 -r 0xea6225212005e86a4490018ded4bf37f3e772161 -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c out`

In second terminal:

`python cic_ussd/import_users.py -v -c config out`

The balance script is a celery task worker, and will not exit by itself in its current version. However, after it's done doing its job, you will find "reached nonce ... exiting" among the last lines of the log.

The connection parameters for the `cic-ussd-server` is currently _hardcoded_ in the `import_users.py` script file.


### Step 4 - Metadata import (optional)

The metadata import scripts can be run at any time after step 1 has been completed.


#### Importing user metadata

To import the main user metadata structs, run:

`node cic_meta/import_meta.js <datadir> <number_of_users>`

Monitors a folder for output from the `import_users.py` script, adding the metadata found to the `cic-meta` service.

If _number of users_ is omitted the script will run until manually interrupted.


#### Importing phone pointer

**IMPORTANT** If you imported using `cic_ussd`, the phone pointer is _already added_ and this script should _NOT_ be run.

`node cic_meta/import_meta_phone.js <datadir> <number_of_users>`


### Step 5 - Verify

`python verify.py -v -c config -r <cic_registry_address> -p <eth_provider> <datadir>` 

Included checks:
* Private key is in cic-eth keystore
* Address is in accounts index
* Address has gas balance
* Address has triggered the token faucet
* Address has token balance matching the gift threshold 
* Metadata can be retrieved and has exact match

Checks can be selectively included and excluded. See `--help` for details.

Will output one line for each check, with name of check and number of errors found per check.

Should exit with code 0 if all input data is found in the respective services.


## KNOWN ISSUES

- If the faucet disbursement is set to a non-zero amount, the balances will be off. The verify script needs to be improved to check the faucet amount.

- When the account callback in `cic_eth` fails, the `cic_eth/import_users.py` script will exit with a cryptic complaint concerning a `None` value.

- Sovereign import scripts use the same keystore, and running them simultaneously will mess up the transaction nonce sequence. Better would be to use two different keystore wallets so balance and users scripts can be run simultaneously.
