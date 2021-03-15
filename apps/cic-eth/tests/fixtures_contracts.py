# standard imports
import json
import hashlib

# external imports
import pytest
from eth_accounts_index import AccountRegistry
from chainlib.eth.nonce import NodeNonceOracle
from hexathon import add_0x

# local imports
from cic_registry.registry import Registry
from cic_registry.encoding import to_identifier

@pytest.fixture(scope='function')
def accounts_registry(
        registry,
        eth_signer,
        eth_rpc,
        accounts,
        default_chain_spec,
        default_chain_config,
        ):

    nonce_oracle = NodeNonceOracle(accounts[0], eth_rpc)
    c = Registry(signer=eth_rpc.signer, nonce_oracle=nonce_oracle)

    chain_spec_identifier = to_identifier(str(default_chain_spec))

    h = hashlib.new('sha256')
    j = json.dumps(default_chain_config)
    h.update(j.encode('utf-8'))
    z = h.digest()
    chain_config_digest = add_0x(z.hex())
    o = c.set(registry, accounts[0], 'AccountsRegistry', accounts[1], chain_spec_identifier, chain_config_digest)
