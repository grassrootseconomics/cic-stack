# standard imports
import os
import datetime
import logging
import json

# external imports
import pytest

# local imports
from cic_cache import db
from cic_cache import BloomCache
from cic_cache.cache import DataCache

logg = logging.getLogger()


def test_cache(
        init_database,
        list_defaults,
        list_actors,
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
        txs,
        tag_txs,
        ):

    session = init_database

    c = DataCache(session)
    b = c.load_transactions_with_data(0, 3) #410000, 420000) #, 100, block_offset=410000, block_limit=420000, oldest=True)

    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == txs[0]
    assert b[2][0]['tx_type'] == 'unknown'
    assert b[2][1]['tx_type'] == 'test.taag'


def test_cache_ranges(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        more_txs,
        ):

    session = init_database
       
    oldest = list_defaults['block'] - 1
    mid = list_defaults['block']
    newest = list_defaults['block'] + 2

    c = BloomCache(session)
    b = c.load_transactions(0, 100)
    assert b[0] == oldest
    assert b[1] == newest

    b = c.load_transactions(1, 2)
    assert b[0] == oldest
    assert b[1] == mid

    b = c.load_transactions(0, 2)
    assert b[0] == mid
    assert b[1] == newest

    b = c.load_transactions(0, 1)
    assert b[0] == newest
    assert b[1] == newest

    b = c.load_transactions(0, 100, oldest=True)
    assert b[0] == oldest
    assert b[1] == newest

    b = c.load_transactions(0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest

    b = c.load_transactions(0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == oldest
    assert b[1] == mid

    b = c.load_transactions(0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'], oldest=True)
    assert b[0] == oldest
    assert b[1] == mid

    # now check when supplying account
    b = c.load_transactions_account(list_actors['alice'], 0, 100)
    assert b[0] == oldest
    assert b[1] == newest

    b = c.load_transactions_account(list_actors['bob'], 0, 100)
    assert b[0] == mid
    assert b[1] == mid

    b = c.load_transactions_account(list_actors['diane'], 0, 100)
    assert b[0] == oldest
    assert b[1] == newest

    # add block filter to the mix
    b = c.load_transactions_account(list_actors['alice'], 0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest
    
    b = c.load_transactions_account(list_actors['alice'], 0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest

    b = c.load_transactions_account(list_actors['bob'], 0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == mid

    b = c.load_transactions_account(list_actors['diane'], 0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == oldest
    assert b[1] == oldest


def test_cache_ranges_data( 
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        more_txs,
        ):

    session = init_database
       
    oldest = list_defaults['block'] - 1
    mid = list_defaults['block']
    newest = list_defaults['block'] + 2

    c = DataCache(session)

    b = c.load_transactions_with_data(0, 100)
    assert b[0] == oldest
    assert b[1] == newest
    assert len(b[2]) == 3
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][2]['tx_hash'] == more_txs[2]

    b = c.load_transactions_with_data(1, 2)
    assert b[0] == oldest
    assert b[1] == mid
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[1]
    assert b[2][1]['tx_hash'] == more_txs[2]

    b = c.load_transactions_with_data(0, 2)
    assert b[0] == mid
    assert b[1] == newest
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[1]

    b = c.load_transactions_with_data(0, 1)
    assert b[0] == newest
    assert b[1] == newest
    assert len(b[2]) == 1
    assert b[2][0]['tx_hash'] == more_txs[0]

    b = c.load_transactions_with_data(0, 100, oldest=True)
    assert b[0] == oldest
    assert b[1] == newest
    assert len(b[2]) == 3
    assert b[2][0]['tx_hash'] == more_txs[2]
    assert b[2][1]['tx_hash'] == more_txs[1]
    assert b[2][2]['tx_hash'] == more_txs[0]

    b = c.load_transactions_with_data(0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[1]

    b = c.load_transactions_with_data(0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == oldest
    assert b[1] == mid
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[1]
    assert b[2][1]['tx_hash'] == more_txs[2]

    b = c.load_transactions_with_data(0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'], oldest=True)
    assert b[0] == oldest
    assert b[1] == mid
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[2]
    assert b[2][1]['tx_hash'] == more_txs[1]

    # now check when supplying account
    b = c.load_transactions_account_with_data(list_actors['alice'], 0, 100)
    assert b[0] == oldest
    assert b[1] == newest
    assert len(b[2]) == 3
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[1]
    assert b[2][2]['tx_hash'] == more_txs[2]

    b = c.load_transactions_account_with_data(list_actors['bob'], 0, 100)
    assert b[0] == mid
    assert b[1] == mid
    assert len(b[2]) == 1
    assert b[2][0]['tx_hash'] == more_txs[1]

    b = c.load_transactions_account_with_data(list_actors['diane'], 0, 100)
    assert b[0] == oldest
    assert b[1] == newest
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[2]

    # add block filter to the mix
    b = c.load_transactions_account_with_data(list_actors['alice'], 0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[1]

    b = c.load_transactions_account_with_data(list_actors['alice'], 0, 100, block_offset=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == newest
    assert len(b[2]) == 2
    assert b[2][0]['tx_hash'] == more_txs[0]
    assert b[2][1]['tx_hash'] == more_txs[1]

    b = c.load_transactions_account_with_data(list_actors['bob'], 0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == mid
    assert b[1] == mid
    assert len(b[2]) == 1
    assert b[2][0]['tx_hash'] == more_txs[1]

    b = c.load_transactions_account_with_data(list_actors['diane'], 0, 100, block_offset=list_defaults['block'] - 1, block_limit=list_defaults['block'])
    assert b[0] == oldest
    assert b[1] == oldest
    assert len(b[2]) == 1
    assert b[2][0]['tx_hash'] == more_txs[2]
