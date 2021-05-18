# standard imports
import json

# local imports
from cic_cache.runnable.daemons.query import process_transactions_all_data


def test_api_all_data(
        init_database,
        txs,
        ):

    env = {
        'PATH_INFO': '/tx/0/100',
        'HTTP_X_CIC_CACHE_MODE': 'all',
            }
    j = process_transactions_all_data(init_database, env)
    o = json.loads(j[1])
    
    assert len(o['data']) == 2
