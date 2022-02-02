# DATA GENERATION TOOLS

This folder contains tools to generate and import test data.

The steps outlines in this document assume you are running the services using the docker-compose orchestration provided.

*A description of manual and service-agnostic steps for imports will be linked here when it becomes available.*


## OVERVIEW

Three sets of tools are available, sorted by respective subdirectories.

- **eth**: Import using sovereign wallets.
- **cic_eth**: Import using the `cic_eth` custodial engine.
- **cic_ussd**: Import using the `cic_ussd` interface (backed by `cic_eth`)

Each of the modules include two main scripts:

- **import_users.py**: Registers all created accounts in the network
- **import_balance.py**: Transfer an opening balance using an external keystore wallet

The balance script will sync with the blockchain, processing transactions and triggering actions when it finds. In its current version it does not keep track of any other state, so it will run indefinitly and needs You the Human to decide when it has done what it needs to do.

In addition the following common tools are available:

- **create_import_users.py**: User creation script
- **verify.py**: Import verification script
- **cic_meta**: Metadata imports

## REQUIREMENTS

A virtual environment for the python scripts is recommended. We know it works with `python 3.8.x`. Let us know if you run it successfully with other minor versions.

```
python3 -m venv .venv
source .venv/bin/activate
```

Install all requirements from the `requirements.txt` file:

`pip install --extra-index-url https://pip.grassrootseconomics.net -r requirements.txt`

If you are importing metadata, also do ye olde:

`npm install`

**wanna help remove this nodejs step from the recipe?** Then click [here](https://gitlab.com/grassrootseconomics/cic-internal-integration/-/issues/227)

## HOW TO USE

### Step 1 - Data creation

Before running any of the imports, the user data to import has to be generated and saved to disk.

The script does not need any services to run.

Vanilla version:

`python create_import_users.py [--dir <datadir>] <number_of_users>`

If you want to use a `import_balance.py` script to add to the user's balance from an external address, use:

`python create_import_users.py --gift-threshold <max_units_to_send> [--dir <datadir>] <number_of_users>`

### Step 2 - Services

The different import modes and steps rely on different combinations of services to be running. 

Listed below is a service dependency table with services referred to by names tha the root docker-compose uses.



| import| services |
|---|---|
| eth | evm |
| cic-eth | evm, postgres, redis, cic-eth-tasker, cic-eth-tracker, cic-eth-dispatcher |
| cic-ussd | evm, postgres, redis, cic-eth-tasker, cic-eth-tracker, cic-eth-dispatcher, cic-user-tasker, cic-user-ussd-server, cic-meta-server |
| cic-meta | cic-meta-server |


### Step 3 - User imports

If you have not changed the docker-compose setup, your `eth_provider` the you need for the commands below will be `http://localhost:63545`.

The keystore file used for transferring external opening balances tracker is relative to the directory you found this README in. Of course you can use a different wallet, but then you will have to provide it with tokens yourself (hint: `../reset.sh`)

All external balance transactions are saved in raw wire format in `<datadir>/tx`, with transaction hash as file name.

If no token symbol is provided on the command line, the default token in the registry will be used.


#### Running the syncer 

It is recommended to run the `sync` script first. This script is responsible for detecting user registrations, and perform actions depending on the regsitration completing first.

The invocation in each case will then be:

`<module>/sync.py -i <chain_spec> -y <key_file> -p <eth_provider> -r <cic_registry_address> <users_dir>`

**Wwant to help reducing the amount of arguments?** Then click [here](https://gitlab.com/grassrootseconomics/cic-internal-integration/-/issues/224)

Now, only run _one_ of the following alternatives.


#### Alternative 1 - Sovereign wallet import - `eth`

`python eth/seed.py -v -p <eth_provider> -r <cic_registry_address> -y <key_file> <user_dir>`

After the script completes, keystore files for all generated accouts will be found in `<datadir>/keystore`, all with `foo` as password (would set it empty, but believe it or not some interfaces out there won't work unless you have one).

#### Alternative 2 - Custodial engine import - `cic_eth`

`python cic_eth/seed.py -v --redis-host-callback <redis_hostname_in_docker> <user_dir>`

The `redis_hostname_in_docker` value is the hostname required to reach the redis server from within the docker cluster, and should be `redis` if you left the docker-compose unchanged.

The `seed.py` script will receive the address of each newly created custodial account on a redis subscription fed by a callback task in the `cic_eth` account creation task chain.

#### Alternative 3 - USSD import - `cic_ussd`

`python cic_ussd/seed.py -v --ussd-provider <ussd_endpoint> <user_dir>`

The script interacts with the ussd endpoint, triggering an account creation.


### Step 4 - Metadata import (optional)

The metadata imports in `./cic_meta/` can be run at any time after step 1 has been completed.


#### Importing user metadata

To import the main user metadata structs, run:

`node cic_meta/import_meta.js <datadir> <number_of_users>`

Monitors a folder for output from the `import_users.py` script, adding the metadata found to the `cic-meta` service.

If _number of users_ is omitted the script will run until manually interrupted.


### Step 5 - Verify

`python verify.py -v -c config -r <cic_registry_address> -p <eth_provider> --token-symbol <token_symbol> <datadir>`

Certain checks are relevant only in certain cases. Here is an overview of which ones apply:

| test | mode | check performed |
|---|---|---|
| local_key | cic_eth |  Private key is in cic-eth keystore |
| accounts_index | all | Address is in accounts index |
| gas | all | Address has gas balance |
| faucet | all | Address has triggered the token faucet |
| balance | all | Address has token balance matching the gift threshold |
| metadata | cic_meta | Personal metadata can be retrieved and has exact match |
| metadata_custom | cic_meta | Custom metadata can be retrieved and has exact match |
| metadata_phone | cic_ussd |  Phone pointer metadata can be retrieved and matches address |
| ussd | cic_ussd | menu response is initial state after registration |

Checks can be selectively included and excluded. See `--help` for details.

Will output one line for each check, with name of check and number of accounts successfully checked for each one.

Should exit with code 0 if all input data is found in the respective services.


## KNOWN ISSUES

- When the account callback in `cic_eth` fails, the `cic_eth/seed.py` script will exit with a cryptic complaint concerning a `None` value.

- Sovereign import scripts use the same keystore, and running them simultaneously will mess up the transaction nonce sequence. Better would be to use two different keystore wallets so balance and users scripts can be run simultaneously.

- `pycrypto` and `pycryptodome` _have to be installed in that order_. If you get errors concerning `Crypto.KDF` then uninstall both and re-install in that order. Make sure you use the versions listed in `requirements.txt`. `pycryptodome` is a legacy dependency and will be removed as soon as possible.

- Sovereign import script is very slow because it's scrypt'ing keystore files for the accounts that it creates. An improvement would be optional and/or asynchronous keyfile generation.

- MacOS BigSur issue when installing psycopg2: ld: library not found for -lssl -> https://github.com/psycopg/psycopg2/issues/1115#issuecomment-831498953

- A strict constraint is maintained insisting the use of postgresql-12.
