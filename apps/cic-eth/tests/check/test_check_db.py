# local imports
from cic_eth.check.db import health

def test_check_health(
    init_database,
        ):

    assert health()
