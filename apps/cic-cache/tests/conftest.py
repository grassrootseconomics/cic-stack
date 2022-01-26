# standard imports
import os
import sys
import datetime

# external imports
import pytest
import moolb
from chainlib.encode import TxHexNormalizer

# local imports
from cic_cache import db
from cic_cache import BloomCache
from cic_cache.cache import DEFAULT_FILTER_SIZE

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.insert(0, root_dir)

# fixtures
from tests.fixtures_config import *
from tests.fixtures_database import *
from tests.fixtures_celery import *


@pytest.fixture(scope='session')
def balances_dict_fields():
    return {
            'out_pending': 0,
            'out_synced': 1,
            'out_confirmed': 2,
            'in_pending': 3,
            'in_synced': 4,
            'in_confirmed': 5,
    }


@pytest.fixture(scope='function')
def txs(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        ):

    tx_normalize = TxHexNormalizer()

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
        tx_normalize.wallet_address(list_actors['alice']),
        tx_normalize.wallet_address(list_actors['bob']),
        tx_normalize.executable_address(list_tokens['foo']),
        tx_normalize.executable_address(list_tokens['foo']),
        1024,
        2048,
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
        tx_normalize.wallet_address(list_actors['diane']),
        tx_normalize.wallet_address(list_actors['alice']),
        tx_normalize.executable_address(list_tokens['foo']),
        tx_normalize.wallet_address(list_tokens['foo']),
        1024,
        2048,
        False,
        dt.timestamp(),
        )
    
    session.commit()

    return [
            tx_hash_first,
            tx_hash_second,
            ]


@pytest.fixture(scope='function')
def more_txs(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        ):

    session = init_database

    tx_normalize = TxHexNormalizer()

    tx_number = 666
    tx_hash = '0x' + os.urandom(32).hex()
    tx_signed = '0x' + os.urandom(128).hex()
    nonce = 3

    dt = datetime.datetime.utcnow()
    dt += datetime.timedelta(hours=1)
    db.add_transaction(
        session,
        tx_hash,
        list_defaults['block']+2,
        tx_number,
        tx_normalize.wallet_address(list_actors['alice']),
        tx_normalize.wallet_address(list_actors['diane']),
        tx_normalize.executable_address(list_tokens['bar']),
        tx_normalize.executable_address(list_tokens['bar']),
        2048,
        4096,
        False,
        dt.timestamp(),
        )

    session.commit()

    return [tx_hash] + txs


@pytest.fixture(scope='function')
def tag_txs(
        init_database,
        txs,
        ):

    db.add_tag(init_database, 'taag', domain='test')
    init_database.commit()

    db.tag_transaction(init_database, txs[1], 'taag', domain='test')


@pytest.fixture(scope='session')
def zero_filter():
    return moolb.Bloom(DEFAULT_FILTER_SIZE, 3)
