# standard imports

# external imports
import pytest
from pytest_redis import factories

# local imports
from cic_ussd.cache import Cache
from cic_ussd.session.ussd_session import UssdSession

redis_test_proc = factories.redis_proc()
redis_db = factories.redisdb('redis_test_proc', decode=True)


@pytest.fixture(scope='function')
def init_cache(redis_db):
    Cache.store = redis_db
    UssdSession.store = redis_db
    return redis_db
