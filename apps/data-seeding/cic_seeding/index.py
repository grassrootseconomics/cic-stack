# standard imports
import logging
import os
import shutil
import sys

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
        return k


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


class AddressQueue:

    def __init__(self, queue_dir):
        self.queue_dir = queue_dir
        self.newdir = os.path.join(queue_dir, 'new')
        self.curdir = os.path.join(queue_dir, 'cur')
        self.deldir = os.path.join(queue_dir, 'del')
        os.makedirs(self.newdir, exist_ok=True)
        os.makedirs(self.curdir, exist_ok=True)
        os.makedirs(self.deldir, exist_ok=True)

        self.c = sys.maxsize
        for v in os.listdir(self.newdir):
            if v[0] == '.':
                continue
            i = 0
            try:
                i = int(v)
            except ValueError:
                logg.warning('skipping alien content in directory: {}'.format(v))

            if i < self.c:
                self.c = i
  
        if self.c == sys.maxsize:
            self.c = 0

        logg.info('start queue index set to {}'.format(self.c))

    
    def tell(self):
        return self.c


    def add(self, k, v):
        if k != None and k != self.c:
            raise ValueError('explicit index value {} does not match current in store: {}'.format(k, self.c))
        fp = os.path.join(self.newdir, str(self.c))
        f = open(fp, 'w')
        f.write(v)
        f.close()
        self.c += 1


    def get(self, k):
        newd = os.path.join(self.newdir, str(k))
        curd = os.path.join(self.curdir, str(k))
        shutil.move(newd, curd)
        f = open(curd, 'r')
        v = f.read()
        f.close()
        return v


    def rm(self, k):
        curd = os.path.join(self.curdir, k)
        deld = os.path.join(self.deldir, k)
        shutil.move(curd, deld)


    def flush(self):
        pass


    def path(self, k):
        if k == None:
            return self.queue_dir
        return os.path.join(self.queue_dir, k)
