# standard imports
import time
import logging
import os
import json

# local imports
from cic_seeding.chain import deserialize_block_tx

logg = logging.getLogger(__name__)


class DeferredSyncer:

    def __init__(self, backend, importer, dirkey, target_count=0, tags=[], pre_callback=None, block_callback=None, post_callback=None):
        self.imp = importer
        self.chain_spec = self.imp.chain_spec
        self.fltr = []
        self.target_count = target_count
        self.tags = tags
        self.dirkey = dirkey
        self.rpc = None
        self.path = self.imp.path(dirkey)


    def add_filter(self, fltr):
        self.fltr.append(fltr)


    def apply_filter(self, i, person, tags=[]):
        u = self.imp.to_user(person)
        try:
            v = self.imp.get(u.address, 'user_block')
        except FileNotFoundError as e:
            logg.debug('cant find file {}'.format(e))
            return
        (block, tx) = deserialize_block_tx(v)
        for fltr in self.fltr:
            fltr.filter(self.rpc, block, tx, db_session=None)


    def loop(self, delay, rpc):
        self.rpc = rpc
        newpath = os.path.join(self.path, 'new')
        while True:
            i = 0
            logg.debug('listing new {}'.format(newpath))
            for k in os.listdir(newpath):
                logg.debug('have {}'.format(k))
                o = self.imp.get(k, self.dirkey)
                (block, tx) = deserialize_block_tx(o)
                
                for fltr in self.fltr:
                    fltr.filter(self.rpc, block, tx, db_session=None)

                i += 1

                #i = self.imp.walk(self.apply_filter, tags=self.tags, dirkey=self.dirkey)
            if i == 0:
                time.sleep(delay)
