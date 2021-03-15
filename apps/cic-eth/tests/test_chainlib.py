# standard imports
import logging

# external imports
from chainlib.eth.connection import RPCConnection
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
        accounts,
        init_eth_tester,
        init_rpc,
        ):

    conn = RPCConnection.connect()
    o = balance(accounts[0])
    conn.do(o)

    o = price()
    conn.do(o)

    o = count_pending(accounts[0])
    conn.do(o)

    o = count_confirmed(accounts[0])
    conn.do(o)


def test_signer(
        init_eth_tester,
        init_rpc,
        accounts,
        ):

    o = sign_message(accounts[0], '0x2a')
    conn = RPCConnection.connect('signer')
    r = conn.do(o)
