# standard imports
import os
import datetime
import logging
import json

# external imports
import pytest

# local imports
from cic_cache import BloomCache
from cic_cache.cache import DataCache

logg = logging.getLogger()


def test_cache(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        ):

    session = init_database

    c = BloomCache(session)
    b = c.load_transactions(0, 100)

    assert b[0] == list_defaults['block'] - 1

    c = BloomCache(session)
    c.load_transactions_account(list_actors['alice'],0, 100)

    assert b[0] == list_defaults['block'] - 1


def test_cache_data(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        tag_txs,
        ):

    session = init_database

    c = DataCache(session)
    b = c.load_transactions_with_data(0, 100)

    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == txs[0]
    assert b[2][0]['tx_type'] == 'unknown'
    assert b[2][1]['tx_type'] == 'test.taag'
    
