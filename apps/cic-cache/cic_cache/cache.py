# standard imports
import logging
import datetime

# external imports
import moolb

# local imports
from cic_cache.db.list import (
        list_transactions_mined,
        list_transactions_account_mined,
        list_transactions_mined_with_data,
        list_transactions_mined_with_data_index,
        list_transactions_account_mined_with_data_index,
        list_transactions_account_mined_with_data,
        )

logg = logging.getLogger()


DEFAULT_FILTER_SIZE = 8192 * 8
DEFAULT_LIMIT = 100

class Cache:

    def __init__(self, session):
        self.session = session


class BloomCache(Cache):

    @staticmethod
    def __get_filter_size(n):
        n = DEFAULT_FILTER_SIZE
        logg.warning('filter size hardcoded to {}'.format(n))
        return n


    def load_transactions(self, offset, limit, oldest=False):
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
        rows = list_transactions_mined(self.session, offset, limit, block_offset=None, block_limit=None, oldest=oldest)

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


    def load_transactions_account(self, address, offset, limit, oldest=False):
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
        rows = list_transactions_account_mined(self.session, address, offset, limit, block_offset=None, block_limit=None, oldest=oldest) 

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


class DataCache(Cache):

    def load_transactions_with_data_index(self, offset, limit, block_offset=None, block_limit=None, oldest=False):
        if limit == 0:
            limit = DEFAULT_LIMIT
        rows = list_transactions_mined_with_data_index(self.session, offset, limit, block_offset, block_limit, oldest=oldest) 
        return self.__load_transactions(rows)


    def load_transactions_with_data(self, offset, limit, block_offset=None, block_limit=None, oldest=False):
        if limit == 0:
            limit = DEFAULT_LIMIT
        rows = list_transactions_mined_with_data(self.session, offset, limit, block_offset, block_limit, oldest=oldest) 
        return self.__load_transactions(rows)


    def load_transactions_account_with_data_index(self, address, offset, limit, block_offset=None, block_limit=None, oldest=False):
        if limit == 0:
            limit = DEFAULT_LIMIT
        rows = list_transactions_account_mined_with_data_index(self.session, address, offset, limit, block_offset, block_limit, oldest=oldest) 
        return self.__load_transactions(rows)

    
    def load_transactions_account_with_data(self, address, offset, limit, block_offset=None, block_limit=None, oldest=False):
        if limit == 0:
            limit = DEFAULT_LIMIT
        rows = list_transactions_account_mined_with_data(self.session, address, offset, limit, block_offset, block_limit, oldest=oldest) 
        return self.__load_transactions(rows)


    def __load_transactions(self, rows):
        tx_cache = []
        highest_block = -1;
        lowest_block = -1;
        date_is_str = None # stick this in startup
        for r in rows:
            if highest_block == -1:
                highest_block = r['block_number']
            lowest_block = r['block_number']
            tx_type = 'unknown'

            if r['value'] != None:
                tx_type = '{}.{}'.format(r['domain'], r['value'])

            if date_is_str == None:
                date_is_str = type(r['date_block']).__name__ == 'str'

            o = {
                'block_number': r['block_number'],
                'tx_hash': r['tx_hash'],
                'date_block': r['date_block'],
                'sender': r['sender'],
                'recipient': r['recipient'],
                'from_value': int(r['from_value']),
                'to_value': int(r['to_value']),
                'source_token': r['source_token'],
                'destination_token': r['destination_token'],
                'success': r['success'],
                'tx_type': tx_type,
            }

            if date_is_str:
                o['date_block'] = datetime.datetime.fromisoformat(r['date_block'])

            tx_cache.append(o)
        return (lowest_block, highest_block, tx_cache)
