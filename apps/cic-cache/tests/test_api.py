# standard imports
import json

# external imports
import pytest

# local imports
from cic_cache.runnable.daemons.query import process_transactions_all_data


def test_api_all_data(
        init_database,
        txs,
        ):

    env = {
        'PATH_INFO': '/txa/100/0/410000/420000',
        'HTTP_X_CIC_CACHE_MODE': 'all',
            }
    j = process_transactions_all_data(init_database, env)
    o = json.loads(j[1])
    
    assert len(o['data']) == 2

    env = {
        'PATH_INFO': '/txa/100/0/420000/410000',
        'HTTP_X_CIC_CACHE_MODE': 'all',
            }
   
    with pytest.raises(ValueError):
        j = process_transactions_all_data(init_database, env)
