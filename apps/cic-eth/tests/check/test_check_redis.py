# external imports
import pytest

# local imports
from cic_eth.check.redis import health


def test_check_redis(
        config,
        have_redis,
        ):

    if have_redis != None:
        pytest.skip('cannot connect to redis, skipping test: {}'.format(have_redis))

    assert health(unit='test', config=config)
