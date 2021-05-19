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

* **create_import_users.py**: User creation script
* **verify.py**: Import verification script
* **cic_meta**: Metadata imports


## REQUIREMENTS

A virtual environment for the python scripts is recommended. We know it works with `python 3.8.x`. Let us know if you run it successfully with other minor versions.

```
python3 -m venv .venv
source .venv/bin/activate
```

Install all requirements from the `requirements.txt` file:

`pip install --extra-index-url https://pip.grassrootseconomics.net:8433 -r requirements.txt`


If you are importing metadata, also do ye olde:

`npm install`


## HOW TO USE

### Step 1 - Data creation

Before running any of the imports, the user data to import has to be generated and saved to disk.

The script does not need any services to run.

Vanilla version:

`python create_import_users.py [--dir <datadir>] <number_of_users>`

If you want to use a `import_balance.py` script to add to the user's balance from an external address, use:

`python create_import_users.py --gift-threshold <max_units_to_send> [--dir <datadir>] <number_of_users>`


### Step 2 - Services

Unless you know what you are doing, start with a clean slate, and execute (in the repository root):

`docker-compose down -v`

Then go through, in sequence:

#### Base requirements

If you are importing using `eth` and _not_ importing metadata, then the only service you need running in the cluster is:
* eth

In all other cases you will _also_ need:
* postgres
* redis


#### EVM provisions

This step is needed in *all* cases.

`RUN_MASK=1 docker-compose up contract-migration`

After this step is run, you can find top-level ethereum addresses (like the cic registry address, which you will need below) in `<repository_root>/service-configs/.env`


#### Custodial provisions
response_data = send_ussd_request(address, self.data_dir)
        state = response_data[:3]
        out = response_data[4:]
        m = '{} {}'.format(state, out[:7])
        if m != 'CON Welcome':
            raise VerifierError(response_data, 'ussd')
This step is _only_ needed if you are importing using `cic_eth` or `cic_ussd`

`RUN_MASK=2 docker-compose up contract-migration`


#### Custodial services

If importing using `cic_eth` or `cic_ussd` also run:
* cic-eth-tasker
* cic-eth-dispatcher
* cic-eth-tracker
* cic-eth-retrier

If importing using `cic_ussd` also run:
* cic-user-tasker
* cic-user-ussd-server
* cic-notify-tasker

If metadata is to be imported, also run:
* cic-meta-server



### Step 3 - User imports

If you did not change the docker-compose setup, your `eth_provider` the you need for the commands below will be `http://localhost:63545`.

Only run _one_ of the alternatives.

The keystore file used for transferring external opening balances tracker is relative to the directory you found this README in. Of course you can use a different wallet, but then you will have to provide it with tokens yourself (hint: `../reset.sh`)

All external balance transactions are saved in raw wire format in `<datadir>/txs`, with transaction hash as file name.



#### Alternative 1 - Sovereign wallet import - `eth` 


First, make a note of the **block height** before running anything.

To import, run to _completion_:

`python eth/import_users.py -v -c config -p <eth_provider> -r <cic_registry_address> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c <datadir>`

After the script completes, keystore files for all generated accouts will be found in `<datadir>/keystore`, all with `foo` as password (would set it empty, but believe it or not some interfaces out there won't work unless you have one).

Then run:

`python eth/import_balance.py -v -c config -r <cic_registry_address> -p <eth_provider> --offset <block_height_at_start> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c <datadir>` 



#### Alternative 2 - Custodial engine import - `cic_eth`

Run in sequence, in first terminal:

`python cic_eth/import_balance.py -v -c config -p <eth_provider> -r <cic_registry_address> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c --head out`

In another terminal:

`python cic_eth/import_users.py -v -c config --redis-host-callback <redis_hostname_in_docker> out`

The `redis_hostname_in_docker` value is the hostname required to reach the redis server from within the docker cluster, and should be `redis` if you left the docker-compose unchanged. The `import_users` script will receive the address of each newly created custodial account on a redis subscription fed by a callback task in the `cic_eth` account creation task chain.


#### Alternative 3 - USSD import - `cic_ussd`

If you have previously run the `cic_ussd` import incompletely, it could be a good idea to purge the queue. If you have left docker-compose unchanged, `redis_url` should be `redis://localhost:63379`.

`celery -A cic_ussd.import_task purge -Q cic-import-ussd --broker <redis_url>`

Then, in sequence, run in first terminal:

`python cic_eth/import_balance.py -v -c config -p <eth_provider> -r <cic_registry_address> -y ../keystore/UTC--2021-01-08T17-18-44.521011372Z--eb3907ecad74a0013c259d5874ae7f22dcbcc95c out`

In second terminal:

`python cic_ussd/import_users.py -v -c config out`


##### Importing pins and ussd data (optional)
Once the user imports are complete the next step should be importing the user's pins and auxiliary ussd data. This can be done in 3 steps:

In one terminal run:

`python create_import_pins.py -c config -v --userdir <path to the users export dir tree> pinsdir <path to pin export dir tree>`

This script will recursively walk through all the directories defining user data in the users export directory and generate a csv file containing phone numbers and password hashes generated using fernet in a manner reflecting the nature of said hashes in the old system.
This csv file will be stored in the pins export dir defined as the positional argument.

Once the creation of the pins file is complete, proceed to import the pins and ussd data as follows:

- To import the pins:

`python cic_ussd/import_pins.py -c config -v pinsdir <path to pin export dir tree>`

- To import ussd data:
`python cic_ussd/import_ussd_data.py -c config -v userdir <path to the users export dir tree>`

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

`node cic_meta/import_meta_phone.js <datadir> <number_of_users>`

If you imported using `cic_ussd`, the phone pointer is _already added_ and this script will do nothing.


### Step 5 - Verify

`python verify.py -v -c config -r <cic_registry_address> -p <eth_provider> <datadir>` 

Included checks:
* Private key is in cic-eth keystore
* Address is in accounts index
* Address has gas balance
* Address has triggered the token faucet
* Address has token balance matching the gift threshold 
* Personal metadata can be retrieved and has exact match
* Phone pointer metadata can be retrieved and matches address
* USSD menu response is initial state after registration

Checks can be selectively included and excluded. See `--help` for details.

Will output one line for each check, with name of check and number of errors found per check.

Should exit with code 0 if all input data is found in the respective services.


## KNOWN ISSUES

- If the faucet disbursement is set to a non-zero amount, the balances will be off. The verify script needs to be improved to check the faucet amount.

- When the account callback in `cic_eth` fails, the `cic_eth/import_users.py` script will exit with a cryptic complaint concerning a `None` value.

- Sovereign import scripts use the same keystore, and running them simultaneously will mess up the transaction nonce sequence. Better would be to use two different keystore wallets so balance and users scripts can be run simultaneously.

- `pycrypto` and `pycryptodome` _have to be installed in that order_. If you get errors concerning `Crypto.KDF` then uninstall both and re-install in that order. Make sure you use the versions listed in `requirements.txt`. `pycryptodome` is a legacy dependency and will be removed as soon as possible.

- Sovereign import script is very slow because it's scrypt'ing keystore files for the accounts that it creates. An improvement would be optional and/or asynchronous keyfile generation.

- Running the balance script should be _optional_ in all cases, but is currently required in the case of `cic_ussd` because it is needed to generate the metadata. An improvement would be moving the task to `import_users.py`, for a different queue than the balance tx handler.

- `cic_ussd` imports is poorly implemented, and consumes a lot of resources. Therefore it takes a long time to complete. Reducing the amount of polls for the phone pointer would go a long way to improve it.
