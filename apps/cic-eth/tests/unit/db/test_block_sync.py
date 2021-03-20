# standard imports
import logging

# local imports
from cic_eth.db.models.otx import OtxSync

logg = logging.getLogger()


def test_db_block_sync(
        init_database,
        ):

    s = OtxSync('eip155:8995:bloxberg')

    s.head(666, 12)
    assert s.head() == (666, 12)

    s.session(42, 13)
    assert s.session() == (42, 13)

    s.backlog(13, 2)
    assert s.backlog() == (13, 2)

    assert not s.synced

    s.backlog(42, 13)
    assert s.backlog() == (42, 13)
    assert s.synced
