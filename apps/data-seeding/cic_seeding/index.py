# standard imports
import logging
import os
import shutil
import sys

# external imports
from chainlib.encode import TxHexNormalizer
from hexathon import strip_0x
from shep.persist import PersistedState
from shep.store.file import SimpleFileStoreFactory
from shep.error import StateItemExists

logg = logging.getLogger(__name__)


tx_normalize = TxHexNormalizer().wallet_address

def normalize_key(k):
        k = strip_0x(k)
        k = tx_normalize(k)
        return k


class AddressIndex:

    def __init__(self, value_filter=None, name=None):
        self.store = {}
        self.value_filter = value_filter
        self.name = name


    def add(self, k, v):
        k = normalize_key(k)
        self.store[k] = v
        return k


    def path(self, k):
        return None


    def get(self, k):
        k = normalize_key(k)
        v = self.store.get(k)
        if self.value_filter != None:
            v = self.value_filter(v)
        return v


    def next(self, k):
        return self.store.next(k)


    def add_from_file(self, file, typ='csv'):
        if typ != 'csv':
            raise NotImplementedError(typ)

        i = 0
        f = open(file, 'r')
        while True:
            r = f.readline()
            r = r.rstrip()
            if len(r) == 0:
                break
            (address, v) = r.split(',', 1)
            address = normalize_key(address)
            self.store[address] = v
            logg.debug('added key {}: {} value {} to {} from file {}'.format(i, address, v, self, file))
            i += 1
       
        logg.debug('added to {}'.format(id(self)))
        return i


    def __str__(self):
        if self.name == None:
            return 'addressindex:{}'.format(id(self))
        return self.name


class AddressQueue(PersistedState):

    def __init__(self, queue_dir, key_normalizer=None):
        self.queue_dir = queue_dir
        factory = SimpleFileStoreFactory(self.queue_dir)
        super(AddressQueue, self).__init__(factory.add, 4)

        self.add('cur')
        self.add('del')

        self.sync(self.NEW)
 

    def get(self, k):
        v = super(AddressQueue, self).get(str(k))
        if v == None:
            raise FileNotFoundError(k)
        return v


    def tell(self):
        v = self.list(self.NEW)
        v.sort()
        logg.info('tell {}'.format(v))
        try:
            r = int(v[0])
        except IndexError:
            return -1
        return r

    
    def list(self, state_name='NEW'):
        state = self.from_name(state_name)
        return super(AddressQueue, self).list(state)

