# TODO: extend blocksync model
class Syncer:
    """Base class and interface for implementing a block sync poller routine.

    :param bc_cache: Retrieves block cache cursors for chain head and latest processed block.
    :type bc_cache: cic_eth.sync.SyncerBackend
    """
    w3 = None
    running_global = True

    def __init__(self, bc_cache):
        self.cursor = None
        self.bc_cache = bc_cache
        self.filter = []
        self.running = True


    def chain(self):
        """Returns the string representation of the chain spec for the chain the syncer is running on.

        :returns: Chain spec string
        :rtype: str
        """
        return self.bc_cache.chain()


    def get(self):
        """Get latest unprocessed blocks.

        :returns: list of block hash strings
        :rtype: list
        """
        raise NotImplementedError()


    def process(self, w3, ref):
        """Process transactions in a single block.

        :param ref: Reference of object to process
        :type ref: str, 0x-hex
        """
        raise NotImplementedError()


    def loop(self, interval):
        """Entry point for syncer loop

        :param interval: Delay in seconds until next attempt if no new blocks are found.
        :type interval: int
        """
        raise NotImplementedError()
