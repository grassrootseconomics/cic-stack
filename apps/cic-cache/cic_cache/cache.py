# standard imports
import logging

# third-party imports
import moolb

# local imports
from cic_cache.db import list_transactions_mined
from cic_cache.db import list_transactions_account_mined

logg = logging.getLogger()


class BloomCache:


    def __init__(self, session):
        self.session = session

    @staticmethod
    def __get_filter_size(n):
        n = 8192 * 8
        logg.warning('filter size hardcoded to {}'.format(n))
        return n


    def load_transactions(self, offset, limit):
        """Retrieves a list of transactions from cache and creates a bloom filter pointing to blocks and transactions.

        Block and transaction numbers are serialized as 32-bit big-endian numbers. The input to the second bloom filter is the concatenation of the serialized block number and transaction index.

        For example, if the block number is 13 and the transaction index is 42, the input are:

        block filter:       0x0d000000
        block+tx filter:    0x0d0000002a0000000

        :param offset: Offset in data set to return transactions from
        :type offset: int
        :param limit: Max number of transactions to retrieve
        :type limit: int
        :return: Lowest block, bloom filter for blocks, bloom filter for blocks|tx
        :rtype: tuple
        """
        rows = list_transactions_mined(self.session, offset, limit) 

        f_block = moolb.Bloom(BloomCache.__get_filter_size(limit), 3)
        f_blocktx = moolb.Bloom(BloomCache.__get_filter_size(limit), 3)
        highest_block = -1
        lowest_block = -1
        for r in rows:
            if highest_block == -1:
                highest_block = r[0]
            lowest_block = r[0]
            block = r[0].to_bytes(4, byteorder='big')
            tx = r[1].to_bytes(4, byteorder='big')
            f_block.add(block)
            f_blocktx.add(block + tx)
            logg.debug('added block {} tx {} lo {} hi {}'.format(r[0], r[1], lowest_block, highest_block))
        return (lowest_block, highest_block, f_block.to_bytes(), f_blocktx.to_bytes(),)


    def load_transactions_account(self, address, offset, limit):
        """Same as load_transactions(...), but only retrieves transactions where the specified account address is sender or recipient.

        :param address: Address to retrieve transactions for.
        :type address: str, 0x-hex
        :param offset: Offset in data set to return transactions from
        :type offset: int
        :param limit: Max number of transactions to retrieve
        :type limit: int
        :return: Lowest block, bloom filter for blocks, bloom filter for blocks|tx
        :rtype: tuple
        """
        rows = list_transactions_account_mined(self.session, address, offset, limit) 

        f_block = moolb.Bloom(BloomCache.__get_filter_size(limit), 3)
        f_blocktx = moolb.Bloom(BloomCache.__get_filter_size(limit), 3)
        highest_block = -1;
        lowest_block = -1;
        for r in rows:
            if highest_block == -1:
                highest_block = r[0]
            lowest_block = r[0]
            block = r[0].to_bytes(4, byteorder='big')
            tx = r[1].to_bytes(4, byteorder='big')
            f_block.add(block)
            f_blocktx.add(block + tx)
            logg.debug('added block {} tx {} lo {} hi {}'.format(r[0], r[1], lowest_block, highest_block))
        return (lowest_block, highest_block, f_block.to_bytes(), f_blocktx.to_bytes(),)
