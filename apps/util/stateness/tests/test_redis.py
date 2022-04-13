# external imports
import pytest
from pytest_redis.plugin import redisdb

# local imports
from stateness.redis import RedisMonitor


class RedisTestMonitor(RedisMonitor):

    def __init__(self, redisdb, domain):
        self.redis = redisdb
        super(RedisMonitor, self).__init__(domain)


    def connect(self):
        pass


def test_redis(redisdb):
    rh = RedisTestMonitor(redisdb, 'foo')

    rh.register('bar')
    rh.set('bar', 'barbarbar')

    v = rh.get('bar')
    assert v == b'barbarbar'


    rh.register('baz')
    rh.set('baz', 42)
    v = rh.get('baz')
    assert v == b'42'


    rh.register('xyzzy')
    rh.inc('xyzzy')
    rh.inc('xyzzy')
    v = rh.get('xyzzy')
    assert v == b'2'


def test_redis_lock(redisdb):
    rh_one = RedisTestMonitor(redisdb, 'foo')
    with pytest.raises(RuntimeError):
        rh_two = RedisTestMonitor(redisdb, 'foo')


def test_redis_unlock(redisdb):
    def redis_init():
        rh_one = RedisTestMonitor(redisdb, 'foo')
    redis_init()
    rh_two = RedisTestMonitor(redisdb, 'foo')


def test_redis_persist(redisdb):
    def redis_init():
        rh_one = RedisTestMonitor(redisdb, 'foo')
        rh_one.register('bar', persist=True)
        rh_one.register('baz')
        rh_one.set('bar', 13)
        rh_one.set('baz', 42)
    redis_init()

    rh_two = RedisTestMonitor(redisdb, 'foo')

    v = rh_two.get('bar')
    assert v == b'13'

    v = rh_two.get('baz')
    assert v == None
