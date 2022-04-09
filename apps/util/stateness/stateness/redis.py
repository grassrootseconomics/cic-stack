# standard imports
import logging

# external imports
import redis

# local imports
from .base import Monitor

logg = logging.getLogger(__name__)


class RedisMonitor(Monitor):

    def __init__(self, domain, host='localhost', port=6379, db=9999):
        self.db = db
        self.host = host
        self.port = port
        self.redis = None
        super(RedisMonitor, self).__init__(domain)


    def connect(self):
        self.redis = redis.Redis(host=self.host, port=self.port, db=self.db)
        

    def load(self):
        ks = self.list()
        if ks == None:
            return
        for k in ks:
            logg.info('domain has persisted key {]'.format(k))
            self.u.append(k)


    def lock(self):
        kk = '_lock.{}'.format(self.domain)
        if self.redis.get(kk) != None:
            raise RuntimeError('domain {} already locked'.format(self.domain))
        self.redis.set(kk, 1)


    def __del__(self):
        for k in self.u:
            if k not in self.persist:
                kk = '.'.join([self.domain, k])
                self.redis.delete(kk)
                logg.info('deleted key {}'.format(k))
            else:
                logg.info('keeping key {}'.format(k))
        kk = '_lock.{}'.format(self.domain)
        self.redis.delete(kk)


    def set(self, k, v):
        if k not in self.u:
            raise KeyError('key {} does not exist in domain {}'.format(k, self.domain))
        kk = '.'.join([self.domain, k])
        self.redis.set(kk, v)


    def inc(self, k):
        kk = '.'.join([self.domain, k])
        v = self.redis.incr(kk)


    def get(self, k):
        kk = '.'.join([self.domain, k])
        return self.redis.get(kk)


    def register(self, k, persist=False):
        if not self.redis.sismember(self.domain, k):
            self.redis.sadd(self.domain, k)
        self.u.append(k)
        if persist:
            self.persist.append(k)


    def list(self):
        self.redis.smembers(self.domain)
