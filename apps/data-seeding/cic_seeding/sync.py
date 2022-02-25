# standard imports
import time
import logging
import os
import json

# external imports
from chainsyncer.error import (
        SyncDone,
        NoBlockForYou,
        )
from chainsyncer.driver.poll import BlockPollSyncer
from chainlib.eth.block import Block
from chainlib.eth.tx import (
        Tx,
        receipt,
        )
from shep.store.file import SimpleFileStoreFactory
from shep.persist import PersistedState
from shep.error import StateItemExists
from shep.error import StateItemNotFound

logg = logging.getLogger(__name__)


class DeferredSyncQueue:

    def __init__(self, queue_dir, semaphore, key_normalizer=None):
        self.queue_dir = queue_dir
        factory = SimpleFileStoreFactory(self.queue_dir).add
        self.key_normalizer = key_normalizer
        self.statestore = PersistedState(factory, 4)
        self.statestore.add('block')
        self.statestore.add('address')
        self.statestore.add('join')
        self.statestore.add('done')
        self.statestore.alias('cur', self.statestore.BLOCK | self.statestore.ADDRESS)
        self.statestore.alias('processing', self.statestore.BLOCK | self.statestore.ADDRESS | self.statestore.JOIN)
        self.statestore.alias('del', self.statestore.BLOCK | self.statestore.ADDRESS | self.statestore.DONE)
        self.wait = semaphore


    # cic_seeding.dirs.QueueInterface
    #def add(self, k, v):
    def put(self, k, v):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        # state=NEW
        return self.statestore.put(k, contents=v) 


    # cic_seeding.dirs.QueueInterface
    def get(self, k):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        return self.statestore.get(k)


    # cic_seeding.dirs.QueueInterface
    def path(self, k):
        return None


    # cic_seeding.dirs.QueueInterface
    def rm(self, k):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        return self.statestore.move(k, self.statestore.DEL)


    def list(self, k='CUR'):
        state = self.statestore.from_name(k)
        return self.statestore.list(state)


    # cic_seeding.dirs.QueueInterface
    def flush(self, k):
        pass


    def sync(self, k='CUR'):
        state = self.statestore.from_name(k)
        self.wait.acquire()
        # this is a wasteful extra resolve of state for name is there a way around it?
        v = self.statestore.sync(state)
        self.wait.release()
        return v


    # May race
    def set_have_block(self, k, block_data):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        #k = str(k)

        self.wait.acquire()

        self.statestore.sync(self.statestore.ADDRESS)

        try:
            v = self.statestore.set(k, self.statestore.BLOCK)
        except StateItemNotFound:
            v = self.statestore.put(k, state=self.statestore.BLOCK)
        self.statestore.replace(k, contents=block_data)

        self.wait.release()
        return v


    # May race
    def set_have_address(self, k):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)
        #k = str(k)

        self.wait.acquire()
      
        self.statestore.sync(self.statestore.BLOCK)
        v = None
        try:
            v = self.statestore.set(k, self.statestore.ADDRESS)
        except StateItemNotFound:
            v = self.statestore.put(k, state=self.statestore.ADDRESS)

        self.wait.release()

        return v


    def set_processing(self, k):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        self.wait.acquire()
        v = self.statestore.move(k, self.statestore.PROCESSING)
        self.wait.release()
        return v


    # No race
    def set_done(self, k):
        if self.key_normalizer != None:
            k = self.key_normalizer(k)

        self.wait.acquire()
        v = self.statestore.move(k, self.statestore.DONE)
        self.wait.release()
        return v


# A syncer implementation that scans a directory for files, parses them as blocks and processes them as transactions.
# Blocks may be randomly accessed.
class DeferredSyncer(BlockPollSyncer):

    def __init__(self, chain_spec, backend, chain_interface, importer, target_count=0, pre_callback=None, block_callback=None, post_callback=None):
        super(DeferredSyncer, self).__init__(backend, chain_interface, pre_callback=pre_callback, block_callback=block_callback, post_callback=post_callback)
        self.imp = importer
        self.chain_spec = chain_spec
        self.target_count = target_count
    

    # Visited by chainsyncer.BlockPollSyncer
    # TODO: Needs to double-check whether we have a matching account in the target import. Otherwise we are blindly sending to anyone registering. Mind to re-insert the entry if fail. Filename should maybe be indexed with number.
    def get(self, conn):
        self.imp.dh.direct('sync', 'ussd_tx_src') #self.queue_store.CUR)
        for k in self.imp.dh.direct('list', 'ussd_tx_src'): #self.queue_store.list(self.queue_store.CUR):
            o = self.imp.get(k, 'ussd_tx_src')
            block = Block(json.loads(o))
            tx = Tx(block.txs[0], block=block)
            self.imp.dh.direct('set_processing', 'ussd_tx_src', k)
            # TODO: avoid this extra lookup
            o = receipt(tx.hash)
            rcpt = conn.do(o)
            tx.apply_receipt(rcpt)
            block.txs = [tx]
            return block
        raise NoBlockForYou()


    # Visited by chainsyncer.BlockPollSyncer
    def process(self, conn, block):
        for tx in block.txs:
            self.process_single(conn, block, tx)
            # TODO: consider avoid extra address processing
            u = self.imp.user_by_tx(tx)
            self.imp.dh.direct('set_done', 'ussd_tx_src', u.address)
        self.backend.reset_filter()
