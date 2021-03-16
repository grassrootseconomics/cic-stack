# standard imports
import logging

# external imports
from chainlib.eth.nonce import NodeNonceOracle
from chainlib.eth.tx import receipt
from eth_accounts_index import AccountRegistry
from contract_registry.registry import (
        Registry,
        )

logg = logging.getLogger()


def test_registry(
        eth_rpc,
        eth_signer,
        registry,
        account_registry,
        roles,
        eth_empty_accounts,
        ):
 
    nonce_oracle = NodeNonceOracle(roles['DEFAULT'], eth_rpc)
    c = Registry(signer=eth_signer, nonce_oracle=nonce_oracle)
    o = c.address_of(registry, 'AccountRegistry', roles['DEFAULT'])
    r = eth_rpc.do(o)
    r = c.parse_address_of(r)
    assert account_registry == r

    nonce_oracle = NodeNonceOracle(roles['ACCOUNT_REGISTRY_WRITER'], eth_rpc)
    c = AccountRegistry(signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.add(account_registry, roles['ACCOUNT_REGISTRY_WRITER'], eth_empty_accounts[0])
    r = eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1
