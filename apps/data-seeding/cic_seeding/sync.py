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

# local imports
from cic_seeding.chain import deserialize_block_tx

logg = logging.getLogger(__name__)


# A syncer implementation that scans a directory for files, parses them as blocks and processes them as transactions.
# Blocks may be randomly accessed.
class DeferredSyncer(BlockPollSyncer):

    def __init__(self, backend, chain_interface, importer, dirkey, target_count=0, tags=[], pre_callback=None, block_callback=None, post_callback=None):
        super(DeferredSyncer, self).__init__(backend, chain_interface, pre_callback=pre_callback, block_callback=block_callback, post_callback=post_callback)
        self.imp = importer
        self.chain_spec = self.imp.chain_spec
        self.target_count = target_count
        self.tags = tags
        self.dirkey = dirkey
        path = self.imp.path(dirkey)
        self.path = os.path.join(path, 'new')
        self.count = 0


    # Visited by chainsyncer.BlockPollSyncer
    def get(self, conn):
        for k in os.listdir(self.path):
            o = self.imp.get(k, self.dirkey)
            block = Block(o)
            return block
        raise NoBlockForYou()


    # Visited by chainsyncer.BlockPollSyncer
    def process(self, conn, block):
        for tx in block.txs:
            self.process_single(conn, block, tx)
        self.backend.reset_filter()
