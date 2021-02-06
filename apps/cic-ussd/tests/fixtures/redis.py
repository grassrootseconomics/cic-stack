# third party imports
import pytest

# local imports
from cic_ussd.redis import InMemoryStore


@pytest.fixture(scope='function')
def init_redis_cache(redisdb):
    InMemoryStore.cache = redisdb
    return redisdb
