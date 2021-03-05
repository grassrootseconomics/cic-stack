# external imports
import celery

# local imports
from cic_eth.db.models.debug import Debug


def test_debug_alert(
        init_database,
        celery_session_worker,
        ):

    s = celery.signature(
            'cic_eth.admin.debug.alert',
            [
                'foo',
                'bar',
                'baz',
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'

    q = init_database.query(Debug)
    q = q.filter(Debug.tag=='bar')
    o = q.first()
    assert o.description == 'baz'
