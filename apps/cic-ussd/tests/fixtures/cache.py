# standard imports

# external imports
import pytest

# local imports
from cic_ussd.cache import Cache
from cic_ussd.session.ussd_session import UssdSession


@pytest.fixture(scope='function')
def init_cache(redisdb):
    Cache.store = redisdb
    UssdSession.store = redisdb
    return redisdb
