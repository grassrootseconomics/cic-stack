# standard imports
import logging

# external imports
from chainlib.connection import RPCConnection
from chainlib.eth.gas import (
        balance,
        price,
        )
from chainlib.eth.tx import (
        count_pending,
        count_confirmed,
        )
from chainlib.eth.sign import (
        sign_message,
        )

logg = logging.getLogger(__name__)


def test_init_eth_tester(
        default_chain_spec,
        eth_accounts,
        init_eth_tester,
        eth_rpc,
        ):

    conn = RPCConnection.connect(default_chain_spec, 'default')
    o = balance(eth_accounts[0])
    conn.do(o)

    o = price()
    conn.do(o)

    o = count_pending(eth_accounts[0])
    conn.do(o)

    o = count_confirmed(eth_accounts[0])
    conn.do(o)


def test_signer(
        default_chain_spec,
        init_eth_tester,
        eth_rpc,
        eth_accounts,
        ):

    o = sign_message(eth_accounts[0], '0x2a')
    conn = RPCConnection.connect(default_chain_spec, 'signer')
    r = conn.do(o)
