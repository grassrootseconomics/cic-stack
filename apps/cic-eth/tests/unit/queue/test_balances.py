# standard imports
import os
import logging

# third-party imports
import pytest

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.queue.balance import (
        balance_outgoing,
        balance_incoming,
        assemble_balances,
        )

logg = logging.getLogger()


def test_assemble():
   
    token_foo = '0x' + os.urandom(20).hex()
    token_bar = '0x' + os.urandom(20).hex()
    b = [
            [
        {
            'address': token_foo,
            'converters': [],
            'balance_foo': 42,
            },
                {
            'address': token_bar,
            'converters': [],
            'balance_baz': 666,
            },
                ],
            [
        {
            'address': token_foo,
            'converters': [],
            'balance_bar': 13,
            },

        {
            'address': token_bar,
            'converters': [],
            'balance_xyzzy': 1337,
            }
            ]
            ]
    r = assemble_balances(b)
    logg.debug('r {}'.format(r))

    assert r[0]['address'] == token_foo
    assert r[1]['address'] == token_bar
    assert r[0].get('balance_foo') != None
    assert r[0].get('balance_bar') != None
    assert r[1].get('balance_baz') != None
    assert r[1].get('balance_xyzzy') != None


@pytest.mark.skip()
def test_outgoing_balance(
        default_chain_spec,
        init_database,
        ):

    chain_str = str(default_chain_spec)
    recipient = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx.add(0, recipient, tx_hash, signed_tx, session=init_database)
    init_database.add(otx)
    init_database.commit()
    
    token_address = '0x' + os.urandom(20).hex()
    sender = '0x' + os.urandom(20).hex()
    txc = TxCache(
            tx_hash,
            sender,
            recipient,
            token_address,
            token_address,
            1000,
            1000,
            )
    init_database.add(txc)
    init_database.commit()

    token_data = {
            'address': token_address,
            'converters': [],
            }
    b = balance_outgoing([token_data], sender, chain_str)
    assert b[0]['balance_outgoing'] == 1000

    otx.sent(session=init_database)
    init_database.commit()

    b = balance_outgoing([token_data], sender, chain_str)
    assert b[0]['balance_outgoing'] == 1000
    
    otx.success(block=1024, session=init_database)
    init_database.commit()

    b = balance_outgoing([token_data], sender, chain_str)
    assert b[0]['balance_outgoing'] == 0


@pytest.mark.skip()
def test_incoming_balance(
        default_chain_spec,
        init_database,
        ):

    chain_str = str(default_chain_spec)
    recipient = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx.add(0, recipient, tx_hash, signed_tx, session=init_database)
    init_database.add(otx)
    init_database.commit()
    
    token_address = '0x' + os.urandom(20).hex()
    sender = '0x' + os.urandom(20).hex()
    txc = TxCache(
            tx_hash,
            sender,
            recipient,
            token_address,
            token_address,
            1000,
            1000,
            )
    init_database.add(txc)
    init_database.commit()

    token_data = {
            'address': token_address,
            'converters': [],
            }
    b = balance_incoming([token_data], recipient, chain_str)
    assert b[0]['balance_incoming'] == 0

    otx.sent(session=init_database)
    init_database.commit()

    b = balance_incoming([token_data], recipient, chain_str)
    assert b[0]['balance_incoming'] == 1000
   
    otx.success(block=1024, session=init_database)
    init_database.commit()

    b = balance_incoming([token_data], recipient, chain_str)
    assert b[0]['balance_incoming'] == 0



