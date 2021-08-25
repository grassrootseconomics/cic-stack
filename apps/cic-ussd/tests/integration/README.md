# INTEGRATION TESTING

This folder contains integration tests.

## OVERVIEW

There are four files defining the integration tests.

* **test_account_creation**: Tests account sign up process.
* **test_transactions**: Tests transactions between two accounts.
* **test_profile_management**: Tests that account metadata can be edited.
* **test_account_management**: Tests that account management functionalities are intact.

## REQUIREMENTS

In order to run the transaction tests, please ensure that the faucet amount is set to a non-zero value, ideally `50000000`
which is the value set in the config file `config/test/integration.ini`.

This implies setting the `DEV_FAUCET_AMOUNT` to a non-zero value before bringing up the contract-migration image:

```shell
export DEV_FAUCET_AMOUNT=50000000
RUN_MASK=1 docker-compose up contract-migration
RUN_MASK=2 docker-compose up contract-migration
```
