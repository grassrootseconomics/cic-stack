# standard imports
import os
import sys
import datetime

# external imports
import pytest

# local imports
from cic_cache import db

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
        list_actors['diane'],
        list_actors['alice'],
        list_tokens['foo'],
        list_tokens['foo'],
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
def tag_txs(
        init_database,
        txs,
        ):

    db.add_tag(init_database, 'taag', domain='test')
    init_database.commit()

    db.tag_transaction(init_database, txs[1], 'taag', domain='test')

