# standard imports
import logging
import json
import hashlib

# external imports
import pytest
from eth_accounts_index import AccountRegistry
from chainlib.eth.nonce import NodeNonceOracle
from hexathon import add_0x
from chainlib.eth.tx import receipt

# local imports
from contract_registry.registry import Registry
from contract_registry.encoding import to_identifier
from contract_registry.pytest.fixtures_registry import valid_identifiers

logg = logging.getLogger(__name__)

valid_identifiers += [
        'AccountRegistry',
        ]


@pytest.fixture(scope='function')
def account_registry(
        registry,
        eth_signer,
        eth_accounts,
        eth_rpc,
        default_chain_spec,
        default_chain_config,
        roles,
        ):

    nonce_oracle = NodeNonceOracle(roles['CONTRACT_DEPLOYER'], eth_rpc)

    c = AccountRegistry(signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.constructor(roles['CONTRACT_DEPLOYER'])
    r = eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1
    account_registry_address = r['contract_address']

    (tx_hash_hex, o) = c.add_writer(account_registry_address, roles['CONTRACT_DEPLOYER'], roles['ACCOUNT_REGISTRY_WRITER'])
    r = eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    c = Registry(signer=eth_signer, nonce_oracle=nonce_oracle)

    chain_spec_identifier = to_identifier(str(default_chain_spec))

    h = hashlib.new('sha256')
    j = json.dumps(default_chain_config)
    h.update(j.encode('utf-8'))
    z = h.digest()
    chain_config_digest = add_0x(z.hex())
    (tx_hash_hex, o) = c.set(registry, roles['CONTRACT_DEPLOYER'], 'AccountRegistry', account_registry_address, chain_spec_identifier, chain_config_digest)
    r = eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    logg.info('accounts registry deployed: {}'.format(account_registry_address))
    return account_registry_address

