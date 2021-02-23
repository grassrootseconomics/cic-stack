# standard imports
import logging

# third-party imports
import web3

# local imports
from .mined import MinedSyncer
from .base import Syncer

logg = logging.getLogger()


class HeadSyncer(MinedSyncer):
    """Implements the get method in Syncer for retrieving every new mined block.

    :param bc_cache: Retrieves block cache cursors for chain head and latest processed block.
    :type bc_cache: Object implementing methods from cic_eth.sync.SyncerBackend 
    """
    def __init__(self, bc_cache):
        super(HeadSyncer, self).__init__(bc_cache)
        # TODO: filter not returning all blocks, at least with ganache. kind of defeats the point, then
        #self.w3_filter = rpc.w3.eth.filter({
        #    'fromBlock': block_offset,
        #    }) #'latest')
        #self.bc_cache.set(block_offset, 0)
        logg.debug('initialized head syncer with offset {}'.format(bc_cache.start()))

    """Implements Syncer.get

    :param w3: Web3 object
    :type w3: web3.Web3
    :returns: Block hash of newly mined blocks. if any
    :rtype: list of str, 0x-hex
    """
    def get(self, w3):
        # Of course, the filter doesn't return the same block dict format as getBlock() so we'll just waste some cycles getting the hashes instead.
        #hashes = []
        #for block in self.w3_filter.get_new_entries():
        #    hashes.append(block['blockHash'])
        #logg.debug('blocks {}'.format(hashes))
        #return hashes
        (block_number, tx_number) = self.bc_cache.get()
        block_hash = []
        try:
            block = w3.eth.getBlock(block_number)
            block_hash.append(block.hash)
        except web3.exceptions.BlockNotFound:
            pass

        return block_hash
