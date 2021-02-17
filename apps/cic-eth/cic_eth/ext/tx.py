# standard imports
import logging
import math

# third-pary imports
import web3
import celery
import moolb
from cic_registry.chain import ChainSpec
from cic_registry.registry import CICRegistry
from hexathon import strip_0x

# local imports
from cic_eth.eth.rpc import RpcClient
from cic_eth.db.models.otx import Otx
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.db.enum import StatusEnum
from cic_eth.eth.token import unpack_transfer
from cic_eth.queue.tx import get_tx_cache
from cic_eth.queue.time import tx_times

celery_app = celery.current_app
logg = logging.getLogger()

MAX_BLOCK_TX = 250


# TODO: Make this method easier to read
@celery_app.task()
def list_tx_by_bloom(bloomspec, address, chain_str):
    """Retrieve external transaction data matching the provided filter

    The bloom filter representation with the following structure (the size of the filter will be inferred from the size of the provided filter data):
        {
            'alg': <str; hashing algorithm, currently only "sha256" is understood>,
            'high': <number; highest block number in matched set>,
            'low': <number; lowest block number in matched set>,
            'filter_rounds': <number; hashing rounds used to generate filter entry>,
            'block_filter': <hex; bloom filter data with block matches>,
            'blocktx_filter': <hex; bloom filter data with block+tx matches>,
        }

    :param bloomspec: Bloom filter data
    :type bloomspec: dict (see description above)
    :param address: Recipient address to use in matching
    :type address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: dict of transaction data as dict, keyed by transaction hash
    :rtype: dict of dict
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    c = RpcClient(chain_spec)
    block_filter_data = bytes.fromhex(bloomspec['block_filter'])
    tx_filter_data = bytes.fromhex(bloomspec['blocktx_filter'])
    databitlen = len(block_filter_data)*8
    block_filter = moolb.Bloom(databitlen, bloomspec['filter_rounds'], default_data=block_filter_data)
    tx_filter = moolb.Bloom(databitlen, bloomspec['filter_rounds'], default_data=tx_filter_data)

    txs = {}
    for block_height in range(bloomspec['low'], bloomspec['high']):
        block_height_bytes = block_height.to_bytes(4, 'big')
        if block_filter.check(block_height_bytes):
            logg.debug('filter matched block {}'.format(block_height))
            block = c.w3.eth.getBlock(block_height, True)

            for tx_index in range(0, len(block.transactions)):
                composite = tx_index + block_height
                tx_index_bytes = composite.to_bytes(4, 'big')
                if tx_filter.check(tx_index_bytes):
                    logg.debug('filter matched block {} tx {}'.format(block_height, tx_index))

                    try:
                        tx = c.w3.eth.getTransactionByBlock(block_height, tx_index)
                    except web3.exceptions.TransactionNotFound:
                        logg.debug('false positive on block {} tx {}'.format(block_height, tx_index))
                        continue
                    tx_address = None
                    tx_token_value = 0
                    try:
                        transfer_data = unpack_transfer(tx['data'])
                        tx_address = transfer_data['to']
                        tx_token_value = transfer_data['amount']
                    except ValueError:
                        logg.debug('not a transfer transaction, skipping {}'.format(tx))
                        continue
                    if address == tx_address:
                        status = StatusEnum.SENT
                        try:
                            rcpt = c.w3.eth.getTransactionReceipt(tx.hash)
                            if rcpt['status'] == 0:
                                pending = StatusEnum.REVERTED
                            else:
                                pending = StatusEnum.SUCCESS
                        except web3.exceptions.TransactionNotFound:
                            pass

                        tx_hash_hex = tx['hash'].hex()

                        token = CICRegistry.get_address(chain_spec, tx['to'])
                        token_symbol = token.symbol()
                        token_decimals = token.decimals()
                        times = tx_times(tx_hash_hex, chain_str)
                        tx_r = {
                            'hash': tx_hash_hex,
                            'sender': tx['from'],
                            'recipient': tx_address,
                            'source_value': tx_token_value,
                            'destination_value': tx_token_value,
                            'source_token': tx['to'],
                            'destination_token': tx['to'],
                            'source_token_symbol': token_symbol,
                            'destination_token_symbol': token_symbol,
                            'source_token_decimals': token_decimals,
                            'destination_token_decimals': token_decimals,
                            'source_token_chain': chain_str,
                            'destination_token_chain': chain_str,
                            'nonce': tx['nonce'],
                                }
                        if times['queue'] != None:
                            tx_r['date_created'] = times['queue']
                        else:
                            tx_r['date_created'] = times['network']
                        txs[tx_hash_hex] = tx_r
                        break
    return txs


# TODO: Surely it must be possible to optimize this
# TODO: DRY this with callback filter in cic_eth/runnable/manager
# TODO: Remove redundant fields from end representation (timestamp, tx_hash)
@celery_app.task()
def tx_collate(tx_batches, chain_str, offset, limit, newest_first=True):
    """Merges transaction data from multiple sources and sorts them in chronological order.

    :param tx_batches: Transaction data inputs
    :type tx_batches: lists of lists of transaction data
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param offset: Number of sorted results to skip (not yet implemented)
    :type offset: number
    :param limit: Maximum number of results to return (not yet implemented)
    :type limit: number
    :param newest_first: If True, returns results in reverse chronological order
    :type newest_first: bool
    :returns: Transactions
    :rtype: list
    """
    txs_by_block = {}
    chain_spec = ChainSpec.from_chain_str(chain_str)

    for b in tx_batches:
        for v in b.values():
            tx = None
            k = None
            try:
                hx = strip_0x(v)
                tx = unpack_signed_raw_tx(bytes.fromhex(hx), chain_spec.chain_id())
                txc = get_tx_cache(tx['hash'])
                txc['timestamp'] = int(txc['date_created'].timestamp())
                txc['hash'] = txc['tx_hash']
                tx = txc
            except TypeError:
                tx = v
                tx['timestamp'] = tx['date_created']
            k = '{}.{}.{}'.format(tx['timestamp'], tx['sender'], tx['nonce'])
            txs_by_block[k] = tx

    txs = []
    ks = list(txs_by_block.keys())
    ks.sort()
    if newest_first:
        ks.reverse()
    for k in ks:
        txs.append(txs_by_block[k])
    return txs
