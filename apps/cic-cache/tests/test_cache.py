# standard imports
import os
import datetime
import logging
import json

# third-party imports
import pytest

# local imports
from cic_cache import db
from cic_cache import BloomCache

logg = logging.getLogger()


def test_cache(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        ):

    session = init_database

    tx_number = 13 
    tx_hash_first = '0x' + os.urandom(32).hex()
    val = 15000
    nonce = 1
    dt = datetime.datetime.utcnow()
    db.add_transaction(
        session,
        tx_hash_first,
        list_defaults['block'],
        tx_number,
        list_actors['alice'],
        list_actors['bob'],
        list_tokens['foo'],
        list_tokens['foo'],
        True,
        dt.timestamp(),
            )


    tx_number = 42
    tx_hash_second = '0x' + os.urandom(32).hex()
    tx_signed_second = '0x' + os.urandom(128).hex()
    nonce = 1
    dt -= datetime.timedelta(hours=1)
    db.add_transaction(
        session,
        tx_hash_second,
        list_defaults['block']-1,
        tx_number,
        list_actors['diane'],
        list_actors['alice'],
        list_tokens['foo'],
        list_tokens['foo'],
        False,
        dt.timestamp(),
        )
    
    session.commit()

    c = BloomCache(session)
    b = c.load_transactions(0, 100)

    assert b[0] == list_defaults['block'] - 1

    c = BloomCache(session)
    c.load_transactions_account(list_actors['alice'],0, 100)

    assert b[0] == list_defaults['block'] - 1
