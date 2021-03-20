# local imports
from cic_eth.db.models.debug import Debug


def test_debug(
        init_database,
        ):

    o = Debug('foo', 'bar')
    init_database.add(o)
    init_database.commit()

    q = init_database.query(Debug)
    q = q.filter(Debug.tag=='foo')
    o = q.first()
    assert o.description == 'bar'
