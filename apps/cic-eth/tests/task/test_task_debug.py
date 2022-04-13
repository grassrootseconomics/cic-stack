# standard imports
import logging

# external imports
import celery

# local imports
from cic_eth.debug import Debug

logg = logging.getLogger()


def test_debug(
        init_database,
        celery_session_worker,
        ):

    s = celery.signature(
            'cic_eth.debug.debug_add',
            [
                'foo',
                'bar',
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    assert t.successful()

    q = init_database.query(Debug)
    r = q.first()
    assert r.tag == 'foo'
    assert r.description == 'bar'

