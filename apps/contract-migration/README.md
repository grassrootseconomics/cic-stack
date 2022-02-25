# CIC-stack system bootstrap scripts


## 1. Deploy global contracts.

Global contracts are contracts that may or may not be used to contribute to a data store intended for consumption across instances.

In the current version of the scripts, the only contract deployed is the [AddressDeclarator](https://gitlab.com/cicnet/eth-address-index). Also, in the current version, the `AddressDeclarator` is required as a storage backend for some of the instance contracts.



## 2. Deploy instance contracts.

Instance contracts are contracts whose contents are limited to the context of a single custodial engine system.

This includes a registry of contracts used by the engine, as well as registry contracts for user accounts and tokens.

The contracts deployed are the [Contract Registry](https://git.grassecon.net/cicnet/okota/src/branch/master/solidity/RegistryAddressDeclarator.sol) and the [Token Registry](https://git.grassecon.net/cicnet/okota/src/branch/master/solidity/TokenUniqueSymbolIndexAddressDeclarator.sol).


## 3. Deploy token.

Deploys a CIC token, adding it to the token registry.

The first token deployed becomes the default token of the instance.

In the current version of the scripts, two token types may be deployed; [`giftable_erc20_token`](https://gitlab.com/cicnet/eth-erc20) and [`erc20_demurrage_token`](https://gitlab.com/cicnet/erc20-demurrage-token).

Additionally, an [Account Registry](https://git.grassecon.net/cicnet/okota/src/branch/master/solidity/AccountsIndexAddressDeclarator.sol) and a [Faucet](https://gitlab.com/grassrootseconomics/sarafu-faucet/-/blob/master/solidity/MinterFaucet.sol) is deployed for the token.


## 4. Initialize custodial engine.

Adds system accounts to the custodial engine, and unlocks the initialization seal. After this step, the custodial system is ready to use.


## 5. Publish token metadata

Writes mutable token metadata to the meta server, along with mutable pointers to the same data. The mutable pointers are for wallet components (cic-ussd only so far) to display information about the token.


## 6. Data seeding

This step does not actually execute seeding (yet), but executes a smart contract transaction required for the code in data-seeding to work. See `../apps/data-seeding/README.md` for more information on how to run data-seeding manually.


## Runlevel dependency graph

| step | level | cumulative level | mode | services | description |
|---|---|---|---|---|---|
| 0 | 0 | 0 | any | - | prints last configuration and exists |
| 1 | 1 | 1 | non-custodial | evm | deploy global contracts |
| 2 | 2 | 3 | non-custodial | evm | deploy instance contracts |
| 3 | 4 | 7 | non-custodial | evm | deploy token |
| 4 | 8 | 15 | custodial | evm, postgres, redis, cic-eth-tasker | deploy custodial contracts |
| 5 | 16 | 31 | non-custodial | cic-meta | publish meta proof for deployed token |
| 6 | 32 | 63 | development | evm | prepare data seeding for development |
