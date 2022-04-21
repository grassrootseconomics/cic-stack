# standard imports
import os

# external imports
from chainlib.eth.tx import Tx

# local imports
from cic_eth.sync.retry import NonceChecker


def test_nonce_gap(
        eth_rpc,
        agent_roles,
        ):
    nonce_checker = NonceChecker(eth_rpc)
    tx = Tx({
        'from': agent_roles['ALICE'],
        'to': agent_roles['BOB'],
        'nonce': 0,
        'hash': os.urandom(32).hex(),
        'value': 42,
        'gasPrice': 100000000,
        'gas': 21000,
        'data': '0x',
        })
    assert nonce_checker.check(tx)
    assert nonce_checker.check(tx)

    tx.nonce = 1
    assert not nonce_checker.check(tx)
