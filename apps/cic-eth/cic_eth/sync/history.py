# standard imports
import logging

# third-party imports
from web3.exceptions import BlockNotFound
from .error import LoopDone

# local imports
from .mined import MinedSyncer
from .base import Syncer
from cic_eth.db.models.base import SessionBase

logg = logging.getLogger()


class HistorySyncer(MinedSyncer):
    """Implements the get method in Syncer for retrieving all blocks between last processed block before previous shutdown and block height at time of syncer start.

    :param bc_cache: Retrieves block cache cursors for chain head and latest processed block.
    :type bc_cache: Object implementing methods from cic_eth.sync.SyncerBackend 
    :param mx: Maximum number of blocks to return in one call
    :type mx: int
    """
    def __init__(self, bc_cache, mx=500):
        super(HistorySyncer, self).__init__(bc_cache)
        self.max = mx

        self.target = bc_cache.target()
        logg.info('History syncer target block number {}'.format(self.target))

        session_offset = self.bc_cache.get()

        self.block_offset = session_offset[0]
        self.tx_offset = session_offset[1]
        logg.info('History syncer starting at {}:{}'.format(session_offset[0], session_offset[1]))

        self.filter = []


    """Implements Syncer.get

    BUG: Should also raise LoopDone when block array is empty after loop.

    :param w3: Web3 object
    :type w3: web3.Web3
    :raises LoopDone: If a block is not found.
    :return: Return a batch of blocks to process
    :rtype: list of str, 0x-hex
    """
    def get(self, w3):
        sync_db = self.bc_cache
        height = self.bc_cache.get()
        logg.debug('height {}'.format(height))
        block_last = height[0]
        tx_last = height[1]
        if not self.running:
            raise LoopDone((block_last, tx_last))
        b = []
        block_target = block_last + self.max
        if block_target > self.target:
            block_target = self.target
        logg.debug('target {} last {} max {}'.format(block_target, block_last, self.max))
        for i in range(block_last, block_target):
            if i == self.target:
                logg.info('reached target {}, exiting'.format(i))
                self.running = False
                break
            bhash = w3.eth.getBlock(i).hash
            b.append(bhash)
            logg.debug('appending block {} {}'.format(i, bhash.hex()))
        if block_last == block_target:
            logg.info('aleady reached target {}, exiting'.format(self.target))
            self.running = False
        return b
