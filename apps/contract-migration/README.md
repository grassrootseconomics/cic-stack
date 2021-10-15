# CIC-stack system bootstrap scripts



## 1. Deploy global contracts.

Global contracts are contracts that may or may not be used to contribute to a data store intended for consumption across instances.

In the current version of the scripts, the only contract deployed is the `AddressDeclarator`. Also, in the current version, the `AddressDeclarator` is required as a storage backend for some of the instance contracts.


## 2. Deploy instance contracts.

Instance contracts are contracts whose contents are limited to the context of a single custodial engine system.

This includes a registry of contracts used by the engine, as well as registry contracts for user accounts and tokens.


## 3. Deploy token.

Deploys a CIC token, adding it to the token registry.

The first token deployed becomes the default token of the instance.

In the current version of the scripts, two token types may be deployed; [`giftable_erc20_token`](https://gitlab.com/cicnet/eth-erc20) and [`erc20_demurrage_token`](https://gitlab.com/cicnet/erc20-demurrage-token).

This step may be run multiple times, as long as the token symbol is different from all previously deployed tokens.


## 4. Initialize custodial engine.

Adds system accounts to the custodial engine, and unlocks the initialization seal. After this step, the custodial system is ready to use.


## Services dependency graph

1. evm
2. bootstrap runlevel 1
3. bootstrap runlevel 2
4. bootstrap runlevel 3
5. redis
6. postgres
7. cic-eth-tasker
8. boostrap runlevel 4
