# standard imports
import logging

# third-party imports
import celery

# local imports
from cic_cache.api import Api

logg = logging.getLogger()


def test_task(
        init_database,
        list_defaults,
        list_actors,
        list_tokens,
        txs,
        celery_session_worker,
        ):

    api = Api(queue=None)
    t = api.list(0, 100)
    r = t.get()
    logg.debug('r {}'.format(r))

    assert r['low'] == list_defaults['block'] - 1
