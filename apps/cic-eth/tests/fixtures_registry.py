# external imports
import pytest
from cic_registry import CICRegistry
from chainlib.chain import ChainSpec
from eth_accounts_index import AccountRegistry

@pytest.fixture(scope='session')
def default_chain_spec():
    return ChainSpec('evm', 'bloxberg', 8996)


@pytest.fixture(scope='session')
def accounts_registry(
        default_chain_spec,
        cic_registry,
        ):
    #abi = AccountRegistry.abi()
    #constructor = w3.eth.contract(abi=abi, bytecode=AccountRegistry.bytecode())
    #tx_hash = constructor.constructor().transact()
    r = w3.eth.getTransactionReceipt(tx_hash) 
    logg.debug('accounts registry deployed {}'.format(r.contractAddress))
    account_registry = AccountRegistry(w3, r.contractAddress)

    c = w3.eth.contract(abi=abi, address=r.contractAddress)
    c.functions.addWriter(w3.eth.accounts[0]).transact()

    CICRegistry.add_contract(default_chain_spec, c, 'AccountRegistry')

    return account_registry
