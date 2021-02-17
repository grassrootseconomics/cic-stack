# standard imports
import logging
import time

# third-party imports
import celery

# local impotes
from .base import Syncer
from cic_eth.queue.tx import set_final_status
from cic_eth.eth import RpcClient

app = celery.current_app
logg = logging.getLogger()


class MinedSyncer(Syncer):
    """Base implementation of block processor for mined blocks.

    Loops through all transactions, 

    :param bc_cache: Retrieves block cache cursors for chain head and latest processed block.
    :type bc_cache: Object implementing methods from cic_eth.sync.SyncerBackend 
    """

    yield_delay = 0.005

    def __init__(self, bc_cache):
        super(MinedSyncer, self).__init__(bc_cache)
        self.block_offset = 0
        self.tx_offset = 0


    def process(self, w3, ref):
        """Processes transactions in a single block, advancing transaction (and block) cursor accordingly.

        :param w3: Web3 object
        :type w3: web3.Web3
        :param ref: Block reference (hash) to process
        :type ref: str, 0x-hex
        :returns: Block number of next unprocessed block
        :rtype: number
        """
        b = w3.eth.getBlock(ref)
        c = w3.eth.getBlockTransactionCount(ref)
        s = 0
        if self.block_offset == b.number:
            s = self.tx_offset

        logg.debug('processing {} (blocknumber {}, count {}, offset {})'.format(ref, b.number, c, s))

        for i in range(s, c):
            tx = w3.eth.getTransactionByBlock(ref, i)
            tx_hash_hex = tx['hash'].hex()
            rcpt = w3.eth.getTransactionReceipt(tx_hash_hex)
            logg.debug('{}/{} processing tx {} from block {} {}'.format(i+1, c, tx_hash_hex, b.number, ref))
            ours = False
            # TODO: ensure filter loop can complete on graceful shutdown
            for f in self.filter:
                #try:
                task_uuid = f(w3, tx, rcpt, self.chain())
                #except Exception as e:
                #    logg.error('error in filter {} tx {}: {}'.format(f, tx_hash_hex, e))
                #    continue
                if task_uuid != None:
                    logg.debug('tx {} passed to celery task {}'.format(tx_hash_hex, task_uuid))
                    s = celery.signature(
                            'set_final_status',
                            [tx_hash_hex, rcpt['blockNumber'], not rcpt['status']],
                            )
                    s.apply_async()
                    break
            next_tx = i + 1
            if next_tx == c:
                self.bc_cache.set(b.number+1, 0)
            else:
                self.bc_cache.set(b.number, next_tx)
        if c == 0:
            logg.info('synced block {} has no transactions'.format(b.number))
            #self.bc_cache.session(b.number+1, 0)
            self.bc_cache.set(b.number+1, 0)
        return b['number']



    def loop(self, interval):
        """Loop running until the "running" property of Syncer is set to False.

        Retrieves latest unprocessed blocks and processes them.

        :param interval: Delay in seconds until next attempt if no new blocks are found.
        :type interval: int
        """
        while self.running and Syncer.running_global:
            self.bc_cache.connect()
            c = RpcClient(self.chain())
            logg.debug('loop execute')
            e = self.get(c.w3)
            logg.debug('got blocks {}'.format(e))
            for block in e:
                block_number = self.process(c.w3, block.hex())
                logg.info('processed block {} {}'.format(block_number, block.hex()))
            self.bc_cache.disconnect()
            if len(e) > 0:
                time.sleep(self.yield_delay)
            else:
                time.sleep(interval)
        logg.info("Syncer no longer set to run, gracefully exiting")
