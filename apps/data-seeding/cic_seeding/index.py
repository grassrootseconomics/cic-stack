# standard imports
import logging

# external imports
from chainlib.encode import TxHexNormalizer
from hexathon import strip_0x

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


    def path(self, k):
        return None


    def get(self, k):
        k = normalize_key(k)
        v = self.store.get(k)
        if self.value_filter != None:
            v = self.value_filter(v)
        return v


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
        
        return i


    def __str__(self):
        if self.name == None:
            return 'addressindex:{}'.format(id(self))
        return self.name
